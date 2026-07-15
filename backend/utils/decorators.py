from functools import wraps

from flask import jsonify, g

from flask_jwt_extended import (
    verify_jwt_in_request,
    get_jwt_identity
)

from models.user import User


def role_required(role):

    def wrapper(fn):

        @wraps(fn)
        def decorated(*args, **kwargs):

            verify_jwt_in_request()

            user_id = int(get_jwt_identity())

            user = User.query.get(user_id)

            if not user:

                return jsonify({
                    "message": "User not found"
                }), 404

            if not user.is_active:
                return jsonify({
                    "message": "Account is deactivated"
                }), 403

            allowed_roles = role if isinstance(role, (list, tuple, set)) else {role}

            if user.role not in allowed_roles:

                return jsonify({
                    "message": "Unauthorized"
                }), 403

            g.current_user = user
            return fn(*args, **kwargs)

        return decorated

    return wrapper


def current_user():
    verify_jwt_in_request()
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    return user
