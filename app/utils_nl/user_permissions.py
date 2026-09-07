from app.constants import PERMISSION_CAN_MAKE_SERVICES_LIVE
from app.utils.user_permissions import (
    all_db_permissions,
    all_ui_permissions,
    organisation_user_permission_names,
    permission_mappings,
    translate_permissions_from_db_to_ui,
    translate_permissions_from_ui_to_db,
)

__all__ = [
    "all_db_permissions",
    "all_ui_permissions",
    "organisation_user_permission_names",
    "organisation_user_permission_options",
    "permission_mappings",
    "permission_options",
    "translate_permissions_from_db_to_ui",
    "translate_permissions_from_ui_to_db",
]

permission_options = (
    ("manage_service", "Instellingen, team en gebruik beheren"),
    ("view_activity", "Dashboard bekijken"),
    ("send_messages", "Berichten versturen"),
    ("manage_templates", "Sjablonen toevoegen en bewerken"),
    ("manage_api_keys", "API-integratie beheren"),
)

organisation_user_permission_options = ((PERMISSION_CAN_MAKE_SERVICES_LIVE, "nieuwe diensten live zetten"),)
