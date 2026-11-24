"""Team application lifecycle, including resumable cluster provisioning."""
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers
from console.repositories.team_application_repo import team_application_repo
from console.services.team_application_provisioner import TeamApplicationProvisioner


class ApplicationError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(message)


class QuotaSerializer(serializers.Serializer):
    cpu_millicores = serializers.IntegerField(min_value=1, max_value=2147483647)
    memory_mib = serializers.IntegerField(min_value=1, max_value=2147483647)
    storage_gib = serializers.IntegerField(min_value=1, max_value=2147483647)


class ApplicationSerializer(serializers.Serializer):
    team_name = serializers.CharField(max_length=64)
    namespace = serializers.RegexField(r"^[a-z](?:[-a-z0-9]{0,31}[a-z0-9])?$", max_length=33)
    useable_regions = serializers.ListField(child=serializers.CharField(max_length=64), min_length=1, max_length=100)
    application_reason = serializers.CharField(max_length=500)
    quota = QuotaSerializer()
    logo = serializers.CharField(max_length=2048, required=False, allow_blank=True, default="")
    previous_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_useable_regions(self, values):
        if len(values) != len(set(values)):
            raise serializers.ValidationError("集群不能重复")
        return values


class ReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    comment = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")

    def validate(self, values):
        if values["decision"] == "rejected" and not values["comment"].strip():
            raise serializers.ValidationError("驳回时请填写原因")
        return values


class TeamApplicationService:
    def __init__(self, repo=team_application_repo, provisioner=None):
        self.repo = repo
        self.provisioner = provisioner or TeamApplicationProvisioner()

    def actor(self, user, enterprise_id):
        if not getattr(user, "user_id", None) or str(getattr(user, "enterprise_id", "")) != str(enterprise_id):
            raise ApplicationError(403, "无权访问该企业的团队申请")

    def list(self, user, enterprise_id, scope="mine", admin=False):
        self.actor(user, enterprise_id)
        if scope not in ("mine", "all"):
            raise ApplicationError(400, "无效的查询范围")
        if scope == "all" and not admin:
            raise ApplicationError(403, "仅平台管理员可查看全部申请")
        return self.repo.list(enterprise_id, None if scope == "all" else user.user_id)

    def submit(self, user, enterprise_id, data):
        self.actor(user, enterprise_id)
        serializer = ApplicationSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        labels = self.provisioner.regions(enterprise_id, values["useable_regions"])
        if labels is None:
            raise ApplicationError(400, "请选择本企业已启用的集群")
        if (self.provisioner.namespace_exists(values["namespace"]) or
                self.provisioner.alias_exists(enterprise_id, values["team_name"])):
            raise ApplicationError(409, "团队名称或命名空间已被使用")
        try:
            with transaction.atomic():
                previous = values.get("previous_id")
                if previous:
                    original = self.repo.locked(enterprise_id, previous)
                    if not original or original.applicant_id != user.user_id or original.status != "rejected":
                        raise ApplicationError(409, "只能重新提交本人已驳回的申请")
                return self.repo.create(
                    enterprise_id=enterprise_id, applicant_id=user.user_id,
                    applicant_name=user.nick_name or str(user.user_id),
                    team_alias=values["team_name"], namespace=values["namespace"],
                    namespace_claim=values["namespace"], alias_claim=values["team_name"],
                    regions=values["useable_regions"], region_labels=labels, quota=values["quota"],
                    reason=values["application_reason"], logo=values["logo"], previous_id=previous)
        except IntegrityError:
            raise ApplicationError(409, "已有同名团队、命名空间申请，或该申请已重新提交") from None

    def review(self, user, enterprise_id, request_id, data, admin=False):
        self.actor(user, enterprise_id)
        if not admin:
            raise ApplicationError(403, "仅平台管理员可审核团队申请")
        serializer = ReviewSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        with transaction.atomic():
            row = self.repo.locked(enterprise_id, request_id)
            if row is None:
                raise ApplicationError(404, "申请不存在")
            if row.status != "pending":
                raise ApplicationError(409, "该申请已处理，请刷新")
            if values["decision"] == "rejected":
                if row.team_id:
                    raise ApplicationError(409, "团队已开始开通，请重试完成开通")
                row.status = "rejected"
            else:
                labels = self.provisioner.regions(enterprise_id, row.regions)
                if labels is None:
                    raise ApplicationError(409, "申请中的集群已停用，请处理集群状态后重试")
                try:
                    applicant = self.provisioner.applicant(row)
                    if not row.team_id:
                        with transaction.atomic():
                            team = self.provisioner.create(row, user)
                        row.team_id, row.team_name = team.tenant_id, team.tenant_name
                        row.save(update_fields=["team_id", "team_name"])
                    for region in row.regions:
                        if region not in row.regions_done:
                            with transaction.atomic():
                                self.provisioner.apply_region(row, region)
                            row.regions_done = row.regions_done + [region]
                            row.save(update_fields=["regions_done"])
                    with transaction.atomic():
                        self.provisioner.grant(row, applicant, user)
                    row.status = "approved"
                    row.provisioning_error = ""
                except Exception:
                    # Do not expose upstream URLs, credentials or raw exception contents.
                    row.provisioning_error = "团队开通未完成，尚未授予申请人权限，请管理员重试审核。"
                    row.save(update_fields=["provisioning_error"])
                    return row
            row.reviewer_id = user.user_id
            row.reviewer_name = user.nick_name or str(user.user_id)
            row.reviewed_at = timezone.now()
            row.comment = values["comment"]
            row.namespace_claim = None
            row.alias_claim = None
            row.save()
            return row


team_application_service = TeamApplicationService()
