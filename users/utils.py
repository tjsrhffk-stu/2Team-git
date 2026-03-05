# users/utils.py
def is_owner(user) -> bool:
    """
    사장 여부 체크
    - profile.user_type == "OWNER" 하나로 통일
    """
    if not getattr(user, "is_authenticated", False):
        return False
    profile = getattr(user, "profile", None)
    return profile is not None and getattr(profile, "user_type", None) == "OWNER"