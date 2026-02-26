def user_flags(request):
    user = getattr(request, "user", None)
    is_owner = False

    if user and getattr(user, "is_authenticated", False):
        try:
            is_owner = hasattr(user, "profile") and user.profile.user_type == "OWNER"
        except Exception:
            is_owner = False

    return {"is_owner": is_owner}