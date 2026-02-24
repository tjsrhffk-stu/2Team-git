# users/utils.py
def is_owner(user) -> bool:
    """
    사장 여부 체크
    - OwnerProfile이 있으면 True
    """
    return hasattr(user, "owner_profile")