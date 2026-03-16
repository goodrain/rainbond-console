# -*- coding: utf-8 -*-
"""
Repository for platform resources including feature flags.
"""
from console.models.main import PlatformFeatureFlag


class PlatformResourcesRepository(object):
    """
    Repository for managing platform resources and feature flags.
    """

    def get_feature_flag(self, feature_name, team_id=None):
        """
        Get a feature flag by name.

        Args:
            feature_name: Name of the feature flag
            team_id: Optional team ID (for future team-scoped flags)

        Returns:
            PlatformFeatureFlag object or None if not found
        """
        try:
            return PlatformFeatureFlag.objects.get(feature_name=feature_name)
        except PlatformFeatureFlag.DoesNotExist:
            return None

    def is_feature_enabled(self, feature_name, team_id=None):
        """
        Check if a feature is enabled.

        Args:
            feature_name: Name of the feature flag
            team_id: Optional team ID (for future team-scoped flags)

        Returns:
            bool: True if feature is enabled, False otherwise
        """
        flag = self.get_feature_flag(feature_name, team_id)
        return flag.enabled if flag else False

    def create_feature_flag(self, feature_name, enabled=False, description=""):
        """
        Create a new feature flag.

        Args:
            feature_name: Name of the feature flag
            enabled: Whether the feature is enabled
            description: Description of the feature

        Returns:
            PlatformFeatureFlag object
        """
        flag, created = PlatformFeatureFlag.objects.get_or_create(
            feature_name=feature_name,
            defaults={
                'enabled': enabled,
                'description': description,
            }
        )
        return flag

    def update_feature_flag(self, feature_name, enabled=None, description=None):
        """
        Update a feature flag.

        Args:
            feature_name: Name of the feature flag
            enabled: New enabled status (optional)
            description: New description (optional)

        Returns:
            PlatformFeatureFlag object or None if not found
        """
        try:
            flag = PlatformFeatureFlag.objects.get(feature_name=feature_name)
            if enabled is not None:
                flag.enabled = enabled
            if description is not None:
                flag.description = description
            flag.save()
            return flag
        except PlatformFeatureFlag.DoesNotExist:
            return None

    def list_feature_flags(self):
        """
        List all feature flags.

        Returns:
            QuerySet of PlatformFeatureFlag objects
        """
        return PlatformFeatureFlag.objects.all()


platform_resources_repo = PlatformResourcesRepository()
