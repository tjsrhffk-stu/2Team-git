# users/utils.py
def is_owner(user) -> bool:
    """
    사장 여부 체크
    - profile.user_type == "OWNER" 인 경우 True
    """
    if not getattr(user, "is_authenticated", False):
        return False
    profile = getattr(user, "profile", None)
    return profile is not None and getattr(profile, "user_type", None) == "OWNER"