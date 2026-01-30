# -*- coding: utf-8 -*-
"""
Gray release view for application-level canary deployments
"""
import logging

from console.exception.main import ServiceHandleException
from console.services.gray_release_service import gray_release_service
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from openapi.auth.authentication import OpenAPIAuthentication
from openapi.auth.permissions import OpenAPIPermissions
from openapi.serializer.app_serializer import (
    GrayReleaseSerializer, GrayReleaseResponseSerializer,
    UpdateGrayRatioSerializer, UpdateGrayRatioResponseSerializer,
    GrayReleaseListItemSerializer
)
from openapi.views.base import TeamAPIView, TeamAppAPIView
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from www.utils.return_message import general_message

logger = logging.getLogger("default")


class GrayReleaseView(TeamAppAPIView):
    @swagger_auto_schema(
        operation_description="应用级灰度发布",
        manual_parameters=[
            openapi.Parameter("team_id", openapi.IN_PATH, description="团队ID", type=openapi.TYPE_STRING),
            openapi.Parameter("region_name", openapi.IN_PATH, description="区域名称", type=openapi.TYPE_STRING),
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用ID", type=openapi.TYPE_INTEGER),
        ],
        request_body=GrayReleaseSerializer(),
        responses={200: GrayReleaseResponseSerializer()},
        tags=['openapi-apps'],
    )
    def post(self, request, app_id, *args, **kwargs):
        """
        Create a gray release for an application

        Parameters:
        - template_id: Application template ID to install in the app
        - domain_name: Domain name for traffic splitting
        - gray_ratio: Gray ratio (0-100), percentage of traffic to new version
        - market_name: Market name (optional, required if install_from_cloud is True)
        - install_from_cloud: Whether to install from cloud market (default: False)
        """
        try:
            serializer = GrayReleaseSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.data

            template_id = data.get("template_id")
            domain_name = data.get("domain_name")
            gray_ratio = data.get("gray_ratio")
            market_name = data.get("market_name", "")
            install_from_cloud = data.get("install_from_cloud", False)

            logger.info(
                "Creating gray release for app {0}: template={1}, domain={2}, ratio={3}".format(
                    app_id, template_id, domain_name, gray_ratio
                )
            )

            # Create gray release
            result = gray_release_service.create_gray_release(
                team=self.team,
                region_name=self.region_name,
                user=self.user,
                app=self.app,
                template_id=template_id,
                domain_name=domain_name,
                gray_ratio=gray_ratio,
                market_name=market_name,
                install_from_cloud=install_from_cloud
            )

            logger.info("Gray release created successfully: {0}".format(result))

            # Return response
            response_data = {
                "app_id": result["app_id"],
                "app_name": result["app_name"],
                "original_service_id": result["original_service_id"],
                "original_service_cname": result["original_service_cname"],
                "original_weight": result["original_weight"],
                "new_service_id": result["new_service_id"],
                "new_service_cname": result["new_service_cname"],
                "new_weight": result["new_weight"],
                "domain_name": result["domain_name"],
                "gray_ratio": result["gray_ratio"]
            }

            result_msg = general_message(200, "success", "灰度发布创建成功", bean=response_data)
            return Response(result_msg, status=status.HTTP_200_OK)

        except ServiceHandleException as e:
            logger.error("Failed to create gray release: {0}".format(e))
            result_msg = general_message(
                e.status_code if hasattr(e, 'status_code') else 500,
                "failed",
                e.msg_show if hasattr(e, 'msg_show') else "灰度发布创建失败"
            )
            return Response(result_msg, status=e.status_code if hasattr(e, 'status_code') else 500)
        except Exception as e:
            logger.exception("Unexpected error creating gray release")
            result_msg = general_message(
                500,
                "failed",
                "灰度发布创建失败: {0}".format(str(e))
            )
            return Response(result_msg, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateGrayRatioView(TeamAppAPIView):
    @swagger_auto_schema(
        operation_description="调整灰度发布流量比例",
        manual_parameters=[
            openapi.Parameter("team_id", openapi.IN_PATH, description="团队ID", type=openapi.TYPE_STRING),
            openapi.Parameter("region_name", openapi.IN_PATH, description="区域名称", type=openapi.TYPE_STRING),
            openapi.Parameter("app_id", openapi.IN_PATH, description="应用ID", type=openapi.TYPE_INTEGER),
        ],
        request_body=UpdateGrayRatioSerializer(),
        responses={200: UpdateGrayRatioResponseSerializer()},
        tags=['openapi-apps'],
    )
    def put(self, request, app_id, *args, **kwargs):
        """
        Update gray ratio for an existing gray release

        Parameters:
        - template_id: Application template ID (group_key)
        - gray_ratio: New gray ratio (0-100), percentage of traffic to new version
        """
        try:
            from console.repositories.gray_release_repo import gray_release_repo
            from console.models.main import GrayReleaseStatus

            serializer = UpdateGrayRatioSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.data

            template_id = data.get("template_id")
            gray_ratio = data.get("gray_ratio")

            logger.info(
                "Updating gray ratio for app {0}, template {1}: ratio={2}".format(
                    app_id, template_id, gray_ratio
                )
            )

            # Find active gray release record by app_id and template_id
            record = gray_release_repo.get_active_record_by_app_and_template(
                self.team.tenant_id, app_id, template_id
            )

            if not record:
                logger.error(f"No active gray release found for app {app_id}, template {template_id}")
                result_msg = general_message(
                    404,
                    "not_found",
                    f"未找到应用 {app_id} 模板 {template_id} 的活跃灰度发布记录"
                )
                return Response(result_msg, status=status.HTTP_404_NOT_FOUND)

            logger.info(f"Found gray release record: ID={record.ID}, domain={record.domain_name}, "
                       f"current_ratio={record.gray_ratio}")

            # Check if this is a full release (gray_ratio=100)
            is_full_release = (gray_ratio == 100)

            if is_full_release:
                logger.info("Full release detected (gray_ratio=100), will delete original services after routing update")
            # Use the record to update gray ratio (doesn't rely on ServiceDomain table)
            result = gray_release_service.update_gray_ratio_by_record(
                team=self.team,
                region_name=self.region_name,
                user=self.user,
                app=self.app,
                record=record,
                new_gray_ratio=gray_ratio,
                is_full_release=is_full_release
            )

            logger.info("Gray ratio updated successfully: {0}".format(result))

            # If full release, delete original services
            if is_full_release and result.get("original_deleted", False):
                logger.info(f"Deleting original services from template: {record.original_upgrade_group_id}")
                try:
                    from console.services.app_actions import app_manage_service
                    from console.services.group_service import group_service

                    # Get all services in original upgrade group
                    original_group_services = group_service.get_group_services(record.original_upgrade_group_id)
                    original_service_ids = [s.service_id for s in original_group_services]

                    if original_service_ids:
                        logger.info(f"Deleting {len(original_service_ids)} original services: {original_service_ids}")

                        # Batch delete services
                        success_count = 0
                        for service_id in original_service_ids:
                            from console.repositories.service_repo import service_repo
                            service = service_repo.get_service_by_service_id(service_id)
                            if service:
                                code, msg = app_manage_service.batch_delete(
                                    self.user, self.team, service, is_force=True
                                )
                                if code == 200:
                                    success_count += 1
                                    logger.info(f"Deleted original service: {service.service_cname} ({service_id})")
                                else:
                                    logger.warning(f"Failed to delete service {service_id}: {msg}")

                        logger.info(f"Successfully deleted {success_count}/{len(original_service_ids)} original services")

                        # Update gray release record status to completed
                        from console.repositories.gray_release_repo import gray_release_repo
                        from console.models.main import GrayReleaseStatus
                        gray_release_repo.update_status(record, GrayReleaseStatus.COMPLETED)
                        logger.info(f"Gray release marked as completed: record_id={record.ID}")

                except Exception as e:
                    logger.exception(f"Failed to delete original services: {e}")
                    # Don't fail the request, just log the error

            # Return response
            response_data = {
                "app_id": result["app_id"],
                "app_name": result["app_name"],
                "original_service_id": result["original_service_id"],
                "original_service_cname": result["original_service_cname"],
                "original_weight": result["original_weight"],
                "new_service_id": result["new_service_id"],
                "new_service_cname": result["new_service_cname"],
                "new_weight": result["new_weight"],
                "domain_name": result["domain_name"],
                "gray_ratio": result["gray_ratio"]
            }

            result_msg = general_message(200, "success", "灰度比例更新成功", bean=response_data)
            return Response(result_msg, status=status.HTTP_200_OK)

        except ServiceHandleException as e:
            logger.error("Failed to update gray ratio: {0}".format(e))
            result_msg = general_message(
                e.status_code if hasattr(e, 'status_code') else 500,
                "failed",
                e.msg_show if hasattr(e, 'msg_show') else "灰度比例更新失败"
            )
            return Response(result_msg, status=e.status_code if hasattr(e, 'status_code') else 500)
        except Exception as e:
            logger.exception("Unexpected error updating gray ratio")
            result_msg = general_message(
                500,
                "failed",
                "灰度比例更新失败: {0}".format(str(e))
            )
            return Response(result_msg, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GrayReleaseListView(APIView):
    authentication_classes = [OpenAPIAuthentication]
    permission_classes = [OpenAPIPermissions]

    @swagger_auto_schema(
        operation_description="查询平台下的灰度发布列表",
        manual_parameters=[
            openapi.Parameter("status", openapi.IN_QUERY, description="状态筛选: active-灰度中, completed-已完成, cancelled-已取消", type=openapi.TYPE_STRING, required=False),
        ],
        responses={200: GrayReleaseListItemSerializer(many=True)},
        tags=['openapi-apps'],
    )
    def get(self, request, *args, **kwargs):
        """
        Get gray release list for the whole platform

        Query parameters:
        - status: Filter by status (active, completed, cancelled)
        """
        try:
            from console.repositories.gray_release_repo import gray_release_repo
            from console.models.main import GrayReleaseRecord

            status_filter = request.GET.get('status', None)

            # Get all gray release records
            queryset = GrayReleaseRecord.objects.all()

            # Filter by status if provided
            if status_filter:
                queryset = queryset.filter(status=status_filter)

            # Order by update time descending
            records = queryset.order_by('-update_time')

            # Convert to response format
            result_list = []
            for record in records:
                import json
                service_mappings = []
                if record.service_mappings:
                    try:
                        service_mappings = json.loads(record.service_mappings)
                    except Exception as e:
                        logger.warning(f"Failed to parse service_mappings for record {record.ID}: {e}")
                        service_mappings = []

                result_list.append({
                    'id': record.ID,
                    'app_id': record.app_id,
                    'app_name': record.app_name,
                    'template_id': record.template_id,
                    'template_name': record.template_name,
                    'template_version': record.template_version,
                    'domain_name': record.domain_name,
                    'gray_ratio': record.gray_ratio,
                    'status': record.status,
                    'service_mappings': service_mappings,
                    'create_time': record.create_time.strftime('%Y-%m-%d %H:%M:%S') if record.create_time else '',
                    'update_time': record.update_time.strftime('%Y-%m-%d %H:%M:%S') if record.update_time else '',
                })

            result_msg = general_message(200, "success", "查询成功", list=result_list)
            return Response(result_msg, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Failed to get gray release list")
            result_msg = general_message(
                500,
                "failed",
                "查询失败: {0}".format(str(e))
            )
            return Response(result_msg, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
