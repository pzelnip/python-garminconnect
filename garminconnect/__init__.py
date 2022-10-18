# -*- coding: utf-8 -*-

"""Python 3 API wrapper for Garmin Connect to get your statistics."""

import json
import logging
import re
import requests
from enum import Enum, auto
from typing import Any, Dict

import cloudscraper


logger = logging.getLogger(__name__)


class ApiClient:
    """Class for a single API endpoint."""

    default_headers = {
        # 'User-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.2 (KHTML, like Gecko) Chrome/15.0.874.121 Safari/535.2'
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:66.0) Gecko/20100101 Firefox/66.0"
    }

    def __init__(self, session, baseurl, headers=None, aditional_headers=None):
        """Return a new Client instance."""
        self.session = session
        self.baseurl = baseurl

        self.headers = headers or self.default_headers.copy()
        if aditional_headers:
            self.headers.update(aditional_headers)

    def set_cookies(self, cookies):
        logger.debug("Restoring cookies for saved session")
        self.session.cookies.update(cookies)

    def get_cookies(self):
        return self.session.cookies

    def clear_cookies(self):
        self.session.cookies.clear()

    def url(self, addurl=None):
        """Return the url for the API endpoint."""

        path = f"https://{self.baseurl}"
        if addurl is not None:
            path += f"/{addurl}"

        return path

    def get(self, addurl, aditional_headers=None, params=None):
        """Make an API call using the GET method."""
        total_headers = self.headers.copy()
        if aditional_headers:
            total_headers.update(aditional_headers)
        url = self.url(addurl)

        logger.debug("URL: %s", url)
        logger.debug("Headers: %s", total_headers)

        try:
            response = self.session.get(url, headers=total_headers, params=params)
            response.raise_for_status()
            # logger.debug("Response: %s", response.content)
            return response
        except Exception as err:
            logger.debug("Response in exception: %s", response.content)
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError("Too many requests") from err
            if response.status_code == 401:
                raise GarminConnectAuthenticationError("Authentication error") from err
            if response.status_code == 403:
                raise GarminConnectConnectionError(f"Forbidden url: {url}") from err

            raise GarminConnectConnectionError(err) from err

    def post(self, addurl, aditional_headers, params, data):
        """Make an API call using the POST method."""
        total_headers = self.headers.copy()
        if aditional_headers:
            total_headers.update(aditional_headers)
        url = self.url(addurl)

        logger.debug("URL: %s", url)
        logger.debug("Headers: %s", total_headers)
        logger.debug("Data: %s", data)

        try:
            response = self.session.post(
                url, headers=total_headers, params=params, data=data
            )
            response.raise_for_status()
            # logger.debug("Response: %s", response.content)
            return response
        except Exception as err:
            logger.debug("Response in exception: %s", response.content)
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError("Too many requests") from err
            if response.status_code == 401:
                raise GarminConnectAuthenticationError("Authentication error") from err
            if response.status_code == 403:
                raise GarminConnectConnectionError(f"Forbidden url: {url}") from err

            raise GarminConnectConnectionError(err) from err


class Garmin:
    """Class for fetching data from Garmin Connect."""

    def __init__(self, email, password, is_cn=False, session_data=None):
        """Create a new class instance."""
        self.session_data = session_data

        self.username = email
        self.password = password
        self.is_cn = is_cn

        self.garmin_connect_base_url = "https://connect.garmin.com"
        self.garmin_connect_sso_url = "sso.garmin.com/sso"
        self.garmin_connect_modern_url = "connect.garmin.com/modern"
        self.garmin_connect_css_url = "https://static.garmincdn.com/com.garmin.connect/ui/css/gauth-custom-v1.2-min.css"

        if self.is_cn:
            self.garmin_connect_base_url = "https://connect.garmin.cn"
            self.garmin_connect_sso_url = "sso.garmin.cn/sso"
            self.garmin_connect_modern_url = "connect.garmin.cn/modern"
            self.garmin_connect_css_url = "https://static.garmincdn.cn/cn.garmin.connect/ui/css/gauth-custom-v1.2-min.css"

        self.garmin_connect_login_url = f"{self.garmin_connect_base_url}/en-US/signin"
        self.garmin_connect_sso_login = "signin"

        self.garmin_connect_devices_url = (
            "proxy/device-service/deviceregistration/devices"
        )
        self.garmin_connect_device_url = "proxy/device-service/deviceservice"
        self.garmin_connect_weight_url = "proxy/weight-service/weight/dateRange"
        self.garmin_connect_daily_summary_url = (
            "proxy/usersummary-service/usersummary/daily"
        )
        self.garmin_connect_metrics_url = "proxy/metrics-service/metrics/maxmet/daily"
        self.garmin_connect_daily_hydration_url = (
            "proxy/usersummary-service/usersummary/hydration/daily"
        )
        self.garmin_connect_personal_record_url = (
            "proxy/personalrecord-service/personalrecord/prs"
        )
        self.garmin_connect_earned_badges_url = "proxy/badge-service/badge/earned"
        self.garmin_connect_adhoc_challenges_url = (
            "proxy/adhocchallenge-service/adHocChallenge/historical"
        )
        self.garmin_connect_badge_challenges_url = (
            "proxy/badgechallenge-service/badgeChallenge/completed"
        )
        self.garmin_connect_available_badge_challenges_url = (
            "proxy/badgechallenge-service/badgeChallenge/available"
        )
        self.garmin_connect_non_completed_badge_challenges_url = (
            "proxy/badgechallenge-service/badgeChallenge/non-completed"
        )
        self.garmin_connect_daily_sleep_url = (
            "proxy/wellness-service/wellness/dailySleepData"
        )
        self.garmin_connect_daily_stress_url = (
            "proxy/wellness-service/wellness/dailyStress"
        )

        self.garmin_connect_rhr = "proxy/userstats-service/wellness/daily"

        self.garmin_connect_user_summary_chart = (
            "proxy/wellness-service/wellness/dailySummaryChart"
        )
        self.garmin_connect_heartrates_daily_url = (
            "proxy/wellness-service/wellness/dailyHeartRate"
        )
        self.garmin_connect_daily_respiration_url = (
            "proxy/wellness-service/wellness/daily/respiration"
        )
        self.garmin_connect_daily_spo2_url = (
            "proxy/wellness-service/wellness/daily/spo2"
        )
        self.garmin_connect_activities = (
            "proxy/activitylist-service/activities/search/activities"
        )
        self.garmin_connect_activity = "proxy/activity-service/activity"

        self.garmin_connect_fit_download = "proxy/download-service/files/activity"
        self.garmin_connect_tcx_download = "proxy/download-service/export/tcx/activity"
        self.garmin_connect_gpx_download = "proxy/download-service/export/gpx/activity"
        self.garmin_connect_kml_download = "proxy/download-service/export/kml/activity"
        self.garmin_connect_csv_download = "proxy/download-service/export/csv/activity"
        self.garmin_connect_gear = "proxy/gear-service/gear/filterGear"

        self.garmin_connect_logout = "auth/logout/?url="

        self.garmin_headers = {"NK": "NT"}

        self.session = cloudscraper.CloudScraper()
        self.sso_rest_client = ApiClient(
            self.session,
            self.garmin_connect_sso_url,
            aditional_headers=self.garmin_headers,
        )
        self.modern_rest_client = ApiClient(
            self.session,
            self.garmin_connect_modern_url,
            aditional_headers=self.garmin_headers,
        )

        self.display_name = None
        self.full_name = None
        self.unit_system = None

    @staticmethod
    def __get_json(page_html, key):
        """Return json from text."""

        if found := re.search(key + r" = (\{.*\});", page_html, re.M):
            json_text = found[1].replace('\\"', '"')
            return json.loads(json_text)

        return None

    def login(self):
        if self.session_data is None:
            return self.authenticate()
        else:
            return self.login_session()

    def login_session(self):
        logger.debug("login with cookies")

        session_display_name = self.session_data["display_name"]
        logger.debug("Set cookies in session")
        self.modern_rest_client.set_cookies(
            requests.utils.cookiejar_from_dict(self.session_data["session_cookies"])
        )
        self.sso_rest_client.set_cookies(
            requests.utils.cookiejar_from_dict(self.session_data["login_cookies"])
        )

        logger.debug("Get page data with cookies")
        params = {
            "service": "https://connect.garmin.com/modern/",
            "webhost": "https://connect.garmin.com",
            "gateway": "true",
            "generateExtraServiceTicket": "true",
            "generateTwoExtraServiceTickets": "true",
        }
        response = self.sso_rest_client.get("login", params=params)
        logger.debug("Session response %s", response.status_code)
        if response.status_code != 200:
            logger.debug("Session expired, authenticating again!")
            return self.authenticate()

        user_prefs = self.__get_json(response.text, "VIEWER_USERPREFERENCES")
        if user_prefs is None:
            logger.debug("Session expired, authenticating again!")
            return self.authenticate()

        self.display_name = user_prefs["displayName"]
        logger.debug("Display name is %s", self.display_name)

        self.unit_system = user_prefs["measurementSystem"]
        logger.debug("Unit system is %s", self.unit_system)

        social_profile = self.__get_json(response.text, "VIEWER_SOCIAL_PROFILE")
        self.full_name = social_profile["fullName"]
        logger.debug("Fullname is %s", self.full_name)

        if self.display_name == session_display_name:
            return True
        logger.debug("Session not valid for user %s", self.display_name)
        return self.authenticate()

    def authenticate(self):
        """Login to Garmin Connect."""

        logger.debug("login: %s %s", self.username, self.password)
        self.modern_rest_client.clear_cookies()
        self.sso_rest_client.clear_cookies()

        get_headers = {"Referer": self.garmin_connect_login_url}
        params = {
            "service": self.modern_rest_client.url(),
            "webhost": self.garmin_connect_base_url,
            "source": self.garmin_connect_login_url,
            "redirectAfterAccountLoginUrl": self.modern_rest_client.url(),
            "redirectAfterAccountCreationUrl": self.modern_rest_client.url(),
            "gauthHost": self.sso_rest_client.url(),
            "locale": "en_US",
            "id": "gauth-widget",
            "cssUrl": self.garmin_connect_css_url,
            "privacyStatementUrl": "//connect.garmin.com/en-US/privacy/",
            "clientId": "GarminConnect",
            "rememberMeShown": "true",
            "rememberMeChecked": "false",
            "createAccountShown": "true",
            "openCreateAccount": "false",
            "displayNameShown": "false",
            "consumeServiceTicket": "false",
            "initialFocus": "true",
            "embedWidget": "false",
            "generateExtraServiceTicket": "true",
            "generateTwoExtraServiceTickets": "false",
            "generateNoServiceTicket": "false",
            "globalOptInShown": "true",
            "globalOptInChecked": "false",
            "mobile": "false",
            "connectLegalTerms": "true",
            "locationPromptShown": "true",
            "showPassword": "true",
        }

        if self.is_cn:
            params[
                "cssUrl"
            ] = "https://static.garmincdn.cn/cn.garmin.connect/ui/css/gauth-custom-v1.2-min.css"

        response = self.sso_rest_client.get(
            self.garmin_connect_sso_login, get_headers, params
        )

        found = re.search(r"name=\"_csrf\" value=\"(\w*)", response.text, re.M)
        if not found:
            logger.error("_csrf not found  (%d)", response.status_code)
            return False

        csrf = found[1]
        referer = response.url
        logger.debug("_csrf found: %s", csrf)
        logger.debug("Referer: %s", referer)

        data = {
            "username": self.username,
            "password": self.password,
            "embed": "false",
            "_csrf": csrf,
        }
        post_headers = {
            "Referer": referer,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        response = self.sso_rest_client.post(
            self.garmin_connect_sso_login, post_headers, params, data
        )

        found = re.search(r"\?ticket=([\w-]*)", response.text, re.M)
        if not found:
            logger.error("Login ticket not found (%d).", response.status_code)
            return False
        params = {"ticket": found[1]}

        response = self.modern_rest_client.get("", params=params)

        user_prefs = self.__get_json(response.text, "VIEWER_USERPREFERENCES")
        self.display_name = user_prefs["displayName"]
        logger.debug("Display name is %s", self.display_name)

        self.unit_system = user_prefs["measurementSystem"]
        logger.debug("Unit system is %s", self.unit_system)

        social_profile = self.__get_json(response.text, "VIEWER_SOCIAL_PROFILE")
        self.full_name = social_profile["fullName"]
        logger.debug("Fullname is %s", self.full_name)

        self.session_data = {
            "display_name": self.display_name,
            "session_cookies": requests.utils.dict_from_cookiejar(
                self.modern_rest_client.get_cookies()
            ),
            "login_cookies": requests.utils.dict_from_cookiejar(
                self.sso_rest_client.get_cookies()
            ),
        }

        logger.debug("Cookies saved")

        return True

    def get_full_name(self):
        """Return full name."""

        return self.full_name

    def get_unit_system(self):
        """Return unit system."""

        return self.unit_system

    def get_stats(self, cdate: str) -> Dict[str, Any]:
        """Return user activity summary for 'cdate' format 'YYYY-mm-dd' (compat for garminconnect)."""

        return self.get_user_summary(cdate)

    def get_user_summary(self, cdate: str) -> Dict[str, Any]:
        """Return user activity summary for 'cdate' format 'YYYY-mm-dd'."""

        url = f"{self.garmin_connect_daily_summary_url}/{self.display_name}"
        params = {"calendarDate": cdate}
        logger.debug("Requesting user summary")

        response = self.modern_rest_client.get(url, params=params).json()

        if response["privacyProtected"] is True:
            raise GarminConnectAuthenticationError("Authentication error")

        return response

    def get_steps_data(self, cdate):
        """Fetch available steps data 'cDate' format 'YYYY-mm-dd'."""

        url = f"{self.garmin_connect_user_summary_chart}/{self.display_name}"
        params = {
            "date": str(cdate),
        }
        logger.debug("Requesting steps data")

        return self.modern_rest_client.get(url, params=params).json()

    def get_heart_rates(self, cdate):  #
        """Fetch available heart rates data 'cDate' format 'YYYY-mm-dd'."""

        url = f"{self.garmin_connect_heartrates_daily_url}/{self.display_name}"
        params = {
            "date": str(cdate),
        }
        logger.debug("Requesting heart rates")

        return self.modern_rest_client.get(url, params=params).json()

    def get_stats_and_body(self, cdate):
        """Return activity data and body composition (compat for garminconnect)."""

        return {
            **self.get_stats(cdate),
            **self.get_body_composition(cdate)["totalAverage"],
        }

    def get_body_composition(self, startdate: str, enddate=None) -> Dict[str, Any]:
        """Return available body composition data for 'startdate' format 'YYYY-mm-dd' through enddate 'YYYY-mm-dd'."""

        if enddate is None:
            enddate = startdate
        url = self.garmin_connect_weight_url
        params = {"startDate": startdate, "endDate": str(enddate)}
        logger.debug("Requesting body composition")

        return self.modern_rest_client.get(url, params=params).json()

    def get_max_metrics(self, cdate: str) -> Dict[str, Any]:
        """Return available max metric data for 'cdate' format 'YYYY-mm-dd'."""

        url = f"{self.garmin_connect_metrics_url}/{cdate}/{cdate}"
        logger.debug("Requesting max metrics")

        return self.modern_rest_client.get(url).json()

    def get_hydration_data(self, cdate: str) -> Dict[str, Any]:
        """Return available hydration data 'cdate' format 'YYYY-mm-dd'."""

        url = f"{self.garmin_connect_daily_hydration_url}/{cdate}"
        logger.debug("Requesting hydration data")

        return self.modern_rest_client.get(url).json()

    def get_respiration_data(self, cdate: str) -> Dict[str, Any]:
        """Return available respiration data 'cdate' format 'YYYY-mm-dd'."""

        url = f"{self.garmin_connect_daily_respiration_url}/{cdate}"
        logger.debug("Requesting respiration data")

        return self.modern_rest_client.get(url).json()

    def get_spo2_data(self, cdate: str) -> Dict[str, Any]:
        """Return available SpO2 data 'cdate' format 'YYYY-mm-dd'."""

        url = f"{self.garmin_connect_daily_spo2_url}/{cdate}"
        logger.debug("Requesting SpO2 data")

        return self.modern_rest_client.get(url).json()

    def get_personal_record(self) -> Dict[str, Any]:
        """Return personal records for current user."""

        url = f"{self.garmin_connect_personal_record_url}/{self.display_name}"
        logger.debug("Requesting personal records for user")

        return self.modern_rest_client.get(url).json()

    def get_earned_badges(self) -> Dict[str, Any]:
        """Return earned badges for current user."""

        url = self.garmin_connect_earned_badges_url
        logger.debug("Requesting earned badges for user")

        return self.modern_rest_client.get(url).json()

    def get_adhoc_challenges(self, start, limit) -> Dict[str, Any]:
        """Return adhoc challenges for current user."""

        url = self.garmin_connect_adhoc_challenges_url
        params = {"start": str(start), "limit": str(limit)}
        logger.debug("Requesting adhoc challenges for user")

        return self.modern_rest_client.get(url, params=params).json()

    def get_badge_challenges(self, start, limit) -> Dict[str, Any]:
        """Return badge challenges for current user."""

        url = self.garmin_connect_badge_challenges_url
        params = {"start": str(start), "limit": str(limit)}
        logger.debug("Requesting badge challenges for user")

        return self.modern_rest_client.get(url, params=params).json()

    def get_available_badge_challenges(self, start, limit) -> Dict[str, Any]:
        """Return available badge challenges."""

        url = self.garmin_connect_available_badge_challenges_url
        params = {"start": str(start), "limit": str(limit)}
        logger.debug("Requesting available badge challenges")
        
        return self.modern_rest_client.get(url, params=params).json()

    def get_non_completed_badge_challenges(self, start, limit) -> Dict[str, Any]:
        """Return badge non-completed challenges for current user."""

        url = self.garmin_connect_non_completed_badge_challenges_url
        params = {"start": str(start), "limit": str(limit)}
        logger.debug("Requesting badge challenges for user")

        return self.modern_rest_client.get(url, params=params).json()

    def get_sleep_data(self, cdate: str) -> Dict[str, Any]:
        """Return sleep data for current user."""

        url = f"{self.garmin_connect_daily_sleep_url}/{self.display_name}"
        params = {"date": cdate, "nonSleepBufferMinutes": 60}

        logger.debug("Requesting sleep data")

        return self.modern_rest_client.get(url, params=params).json()

    def get_stress_data(self, cdate: str) -> Dict[str, Any]:
        """Return stress data for current user."""

        url = f"{self.garmin_connect_daily_stress_url}/{cdate}"
        logger.debug("Requesting stress data")

        return self.modern_rest_client.get(url).json()

    def get_rhr_day(self, cdate: str) -> Dict[str, Any]:
        """Return resting heartrate data for current user."""

        params = {"fromDate": cdate, "untilDate": cdate, "metricId": 60}
        url = f"{self.garmin_connect_rhr}/{self.display_name}"
        logger.debug("Requesting resting heartrate data")

        return self.modern_rest_client.get(url, params=params).json()

    def get_devices(self) -> Dict[str, Any]:
        """Return available devices for the current user account."""

        url = self.garmin_connect_devices_url
        logger.debug("Requesting devices")

        return self.modern_rest_client.get(url).json()

    def get_device_settings(self, device_id: str) -> Dict[str, Any]:
        """Return device settings for device with 'device_id'."""

        url = f"{self.garmin_connect_device_url}/device-info/settings/{device_id}"
        logger.debug("Requesting device settings")

        return self.modern_rest_client.get(url).json()

    def get_device_alarms(self) -> Dict[str, Any]:
        """Get list of active alarms from all devices."""

        logger.debug("Requesting device alarms")

        alarms = []
        devices = self.get_devices()
        for device in devices:
            device_settings = self.get_device_settings(device["deviceId"])
            alarms += device_settings["alarms"]
        return alarms

    def get_device_last_used(self):
        """Return device last used."""

        url = f"{self.garmin_connect_device_url}/mylastused"
        logger.debug("Requesting device last used")

        return self.modern_rest_client.get(url).json()

    def get_activities(self, start, limit):
        """Return available activities."""

        url = self.garmin_connect_activities
        params = {"start": str(start), "limit": str(limit)}
        logger.debug("Requesting activities")

        return self.modern_rest_client.get(url, params=params).json()

    def get_last_activity(self):
        """Return last activity."""

        return activities[-1] if (activities := self.get_activities(0, 1)) else None

    def get_activities_by_date(self, startdate, enddate, activitytype=None):
        """
        Fetch available activities between specific dates
        :param startdate: String in the format YYYY-MM-DD
        :param enddate: String in the format YYYY-MM-DD
        :param activitytype: (Optional) Type of activity you are searching
                             Possible values are [cycling, running, swimming,
                             multi_sport, fitness_equipment, hiking, walking, other]
        :return: list of JSON activities
        """

        activities = []
        start = 0
        limit = 20
        # mimicking the behavior of the web interface that fetches 20 activities at a time
        # and automatically loads more on scroll
        url = self.garmin_connect_activities
        params = {
            "startDate": str(startdate),
            "endDate": str(enddate),
            "start": str(start),
            "limit": str(limit),
        }
        if activitytype:
            params["activityType"] = str(activitytype)

        print(f"Requesting activities by date from {startdate} to {enddate}")
        while True:
            params["start"] = str(start)
            logger.debug(f"Requesting activities {start} to {start+limit}")
            if act := self.modern_rest_client.get(url, params=params).json():
                activities.extend(act)
                start = start + limit
            else:
                break

        return activities

    class ActivityDownloadFormat(Enum):
        """Activitie variables."""

        ORIGINAL = auto()
        TCX = auto()
        GPX = auto()
        KML = auto()
        CSV = auto()

    def download_activity(self, activity_id, dl_fmt=ActivityDownloadFormat.TCX):
        """
        Downloads activity in requested format and returns the raw bytes. For
        "Original" will return the zip file content, up to user to extract it.
        "CSV" will return a csv of the splits.
        """
        activity_id = str(activity_id)
        urls = {
            Garmin.ActivityDownloadFormat.ORIGINAL: f"{self.garmin_connect_fit_download}/{activity_id}",
            Garmin.ActivityDownloadFormat.TCX: f"{self.garmin_connect_tcx_download}/{activity_id}",
            Garmin.ActivityDownloadFormat.GPX: f"{self.garmin_connect_gpx_download}/{activity_id}",
            Garmin.ActivityDownloadFormat.KML: f"{self.garmin_connect_kml_download}/{activity_id}",
            Garmin.ActivityDownloadFormat.CSV: f"{self.garmin_connect_csv_download}/{activity_id}",
        }
        if dl_fmt not in urls:
            raise ValueError(f"Unexpected value {dl_fmt} for dl_fmt")
        url = urls[dl_fmt]

        logger.debug("Downloading activities from %s", url)

        return self.modern_rest_client.get(url).content

    def get_activity_splits(self, activity_id):
        """Return activity splits."""

        activity_id = str(activity_id)
        url = f"{self.garmin_connect_activity}/{activity_id}/splits"
        logger.debug("Requesting splits for activity id %s", activity_id)

        return self.modern_rest_client.get(url).json()

    def get_activity_split_summaries(self, activity_id):
        """Return activity split summaries."""

        activity_id = str(activity_id)
        url = f"{self.garmin_connect_activity}/{activity_id}/split_summaries"
        logger.debug("Requesting split summaries for activity id %s", activity_id)

        return self.modern_rest_client.get(url).json()

    def get_activity_weather(self, activity_id):
        """Return activity weather."""

        activity_id = str(activity_id)
        url = f"{self.garmin_connect_activity}/{activity_id}/weather"
        logger.debug("Requesting weather for activity id %s", activity_id)

        return self.modern_rest_client.get(url).json()

    def get_activity_hr_in_timezones(self, activity_id):
        """Return activity heartrate in timezones."""

        activity_id = str(activity_id)
        url = f"{self.garmin_connect_activity}/{activity_id}/hrTimeInZones"
        logger.debug("Requesting split summaries for activity id %s", activity_id)

        return self.modern_rest_client.get(url).json()

    def get_activity_evaluation(self, activity_id):
        """Return activity self evaluation details."""

        activity_id = str(activity_id)

        url = f"{self.garmin_connect_activity}/{activity_id}"
        logger.debug("Requesting self evaluation data for activity id %s", activity_id)

        return self.modern_rest_client.get(url).json()

    def get_activity_details(self, activity_id, maxchart=2000, maxpoly=4000):
        """Return activity details."""

        activity_id = str(activity_id)
        params = {
            "maxChartSize": str(maxchart),
            "maxPolylineSize": str(maxpoly),
        }
        url = f"{self.garmin_connect_activity}/{activity_id}/details"
        logger.debug("Requesting details for activity id %s", activity_id)

        return self.modern_rest_client.get(url, params=params).json()

    def get_activity_gear(self, activity_id):
        """Return gears used for activity id."""

        activity_id = str(activity_id)
        params = {"activityId": activity_id}
        url = self.garmin_connect_gear
        logger.debug("Requesting gear for activity_id %s", activity_id)

        return self.modern_rest_client.get(url, params=params).json()

    def logout(self):
        """Log user out of session."""

        self.modern_rest_client.get(self.garmin_connect_logout)


class GarminConnectConnectionError(Exception):
    """Raised when communication ended in error."""


class GarminConnectTooManyRequestsError(Exception):
    """Raised when rate limit is exceeded."""


class GarminConnectAuthenticationError(Exception):
    """Raised when authentication is failed."""
