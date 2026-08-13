# accounts/fcm_service.py

import logging
import requests

from django.conf import settings

logger = logging.getLogger(__name__)


class FCMService:
    """
    FCM Service

    تمام ارتباطات ارسال Notification با Firebase
    از طریق Cloudflare Worker انجام می‌شود.

    Django مستقیماً Firebase Admin SDK را استفاده نمی‌کند.
    """

    TOPICS = {
        "ALL_USERS": "all_users",
    }

    # =========================================================
    # WORKER URL
    # =========================================================

    @staticmethod
    def get_worker_url():
        worker_url = getattr(
            settings,
            "FCM_WORKER_URL",
            None
        )

        if not worker_url:
            raise RuntimeError(
                "FCM_WORKER_URL در settings تعریف نشده است."
            )

        return worker_url.rstrip("/")

    # =========================================================
    # CLEAN DATA
    # =========================================================

    @staticmethod
    def clean_data(data=None):
        """
        FCM Data Payload باید فقط string باشد.
        """

        if not data:
            return {}

        clean_data = {}

        for key, value in data.items():

            if value is None:
                continue

            clean_data[str(key)] = str(value)

        return clean_data

    # =========================================================
    # SEND REQUEST TO CLOUDFLARE WORKER
    # =========================================================

    @classmethod
    def _send_to_worker(
        cls,
        title,
        body,
        topic=None,
        token=None,
        data=None,
        image_url=None,
        priority="high",
    ):

        payload = {
            "title": str(title),
            "body": str(body),
            "data": cls.clean_data(data),
            "priority": str(priority),
        }

        if topic:
            payload["topic"] = str(topic)

        if token:
            payload["token"] = str(token)

        if image_url:
            payload["image_url"] = str(image_url)

        worker_url = cls.get_worker_url()

        try:

            logger.info(
                "Sending FCM notification through Cloudflare Worker"
            )

            response = requests.post(
                worker_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                },
                timeout=20,
            )

            # -------------------------------------------------
            # تلاش برای JSON
            # -------------------------------------------------

            try:
                result = response.json()
            except ValueError:

                result = {
                    "success": False,
                    "error": response.text,
                }

            # -------------------------------------------------
            # HTTP ERROR
            # -------------------------------------------------

            if not response.ok:

                logger.error(
                    "FCM Worker HTTP Error: %s",
                    result
                )

                return {
                    "success": False,
                    "message": result.get(
                        "error",
                        "FCM Worker request failed"
                    ),
                    "status_code": response.status_code,
                    "response": result,
                }

            # -------------------------------------------------
            # WORKER ERROR
            # -------------------------------------------------

            if not result.get("success"):

                logger.error(
                    "FCM Worker returned error: %s",
                    result
                )

                return {
                    "success": False,
                    "message": result.get(
                        "error",
                        "FCM Worker failed"
                    ),
                    "response": result,
                }

            # -------------------------------------------------
            # SUCCESS
            # -------------------------------------------------

            logger.info(
                "FCM notification sent successfully through Worker: %s",
                result.get("message_id")
            )

            return {
                "success": True,
                "message": "Notification sent successfully",
                "message_id": result.get("message_id"),
                "response": result,
            }

        except requests.Timeout:

            logger.exception(
                "FCM Worker timeout"
            )

            return {
                "success": False,
                "message": "FCM Worker timeout",
            }

        except requests.RequestException as e:

            logger.exception(
                "FCM Worker connection error"
            )

            return {
                "success": False,
                "message": str(e),
            }

        except Exception as e:

            logger.exception(
                "FCM Worker unexpected error"
            )

            return {
                "success": False,
                "message": str(e),
            }

    # =========================================================
    # SEND TO TOPIC
    # =========================================================

    @classmethod
    def send_to_topic(
        cls,
        topic,
        title,
        body,
        data=None,
        image_url=None,
        priority="high",
    ):

        if not topic:
            return {
                "success": False,
                "message": "Topic الزامی است.",
            }

        if not title:
            return {
                "success": False,
                "message": "Title الزامی است.",
            }

        if not body:
            return {
                "success": False,
                "message": "Body الزامی است.",
            }

        return cls._send_to_worker(
            title=title,
            body=body,
            topic=topic,
            data=data,
            image_url=image_url,
            priority=priority,
        )

    # =========================================================
    # SEND TO SINGLE TOKEN
    # =========================================================

    @classmethod
    def send_to_token(
        cls,
        token,
        title,
        body,
        data=None,
        image_url=None,
        priority="high",
    ):

        if not token:
            return {
                "success": False,
                "message": "FCM Token الزامی است.",
            }

        if not title:
            return {
                "success": False,
                "message": "Title الزامی است.",
            }

        if not body:
            return {
                "success": False,
                "message": "Body الزامی است.",
            }

        return cls._send_to_worker(
            title=title,
            body=body,
            token=token,
            data=data,
            image_url=image_url,
            priority=priority,
        )

    # =========================================================
    # REGISTER TOKEN
    # =========================================================

    @classmethod
    def register_topic(cls, token, topic=None):
        """
        توجه:
        Subscribe شدن به Topic از سمت Android انجام می‌شود.

        Django در این معماری Firebase Admin SDK ندارد.
        """

        topic = topic or cls.TOPICS["ALL_USERS"]

        logger.info(
            "FCM topic registration requested: %s",
            topic
        )

        return {
            "success": True,
            "message": (
                "Topic subscription باید از سمت Android انجام شود."
            ),
            "topic": topic,
        }

    # =========================================================
    # UNSUBSCRIBE TOKEN
    # =========================================================

    @classmethod
    def unregister_topic(cls, token, topic=None):

        topic = topic or cls.TOPICS["ALL_USERS"]

        logger.info(
            "FCM topic unregister requested: %s",
            topic
        )

        return {
            "success": True,
            "message": (
                "Topic unsubscribe باید از سمت Android انجام شود."
            ),
            "topic": topic,
        }