"""Scoped persistence for immutable team application records."""


class TeamApplicationRepository:
    def __init__(self, model=None):
        self._model = model

    @property
    def model(self):
        if self._model is None:
            from console.models.team_application import TeamApplication
            self._model = TeamApplication
        return self._model

    def list(self, enterprise_id, user_id=None):
        rows = self.model.objects.filter(enterprise_id=enterprise_id)
        return rows if user_id is None else rows.filter(applicant_id=user_id)

    def locked(self, enterprise_id, request_id):
        return self.model.objects.select_for_update().filter(enterprise_id=enterprise_id, id=request_id).first()

    def create(self, **values):
        return self.model.objects.create(**values)


team_application_repo = TeamApplicationRepository()
