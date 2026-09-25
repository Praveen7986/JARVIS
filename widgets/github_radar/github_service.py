"""
GitHub Data Engine & Service for GitHub Activity & PR Radar Widget.
Fetches full 52-week contribution calendar matrix, month labels, total contributions,
and user profile data directly matching GitHub's official contribution graph.
"""

import json
import logging
import re
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from PySide6.QtCore import Signal, QThread
from PySide6.QtGui import QPixmap, QImage

logger = logging.getLogger(__name__)


def fetch_github_calendar_html(username: str) -> Dict[str, Any]:
    """
    Fetches official 52-week contribution calendar from GitHub's contributions endpoint.
    Returns parsed daily cells, tooltips, total contributions, and month label positions.
    """
    url = f"https://github.com/users/{username.strip()}/contributions"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to scrape GitHub contributions HTML for {username}: {e}")
        return {}

    # Extract total contribution count and period header (e.g. '21 contributions in 2026')
    h2_match = re.search(r'([0-9,]+)\s+contributions\s+in\s+([^<\n]+)', html, re.I)
    total_count = int(h2_match.group(1).replace(",", "")) if h2_match else 0
    raw_year = h2_match.group(2).strip() if h2_match else ""
    # Clean up year/period label e.g. "2026" or "the last year"
    if "last year" in raw_year.lower():
        period_label = "in the last year"
    elif raw_year:
        period_label = f"in {raw_year}"
    else:
        period_label = f"in {datetime.now().year}"

    # Extract all cells and tooltips
    cells_raw = re.findall(r'<td\s+([^>]+)>', html)
    tooltips = dict(re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]+)</tool-tip>', html))

    days = []
    daily_map = {}
    streak = 0
    cur_streak = 0

    for attr in cells_raw:
        d_m = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', attr)
        if not d_m:
            continue
        date_str = d_m.group(1)

        lvl_m = re.search(r'data-level="(\d+)"', attr)
        level = int(lvl_m.group(1)) if lvl_m else 0

        id_m = re.search(r'id="([^"]+)"', attr)
        cell_id = id_m.group(1) if id_m else ""

        tt = tooltips.get(cell_id, "").strip()
        count = 0
        c_m = re.search(r'(\d+)\s+contribution', tt)
        if c_m:
            count = int(c_m.group(1))
        elif level > 0:
            count = level

        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except Exception:
            continue

        weekday = (dt.weekday() + 1) % 7  # 0 = Sunday, 1 = Monday ... 6 = Saturday
        month_name = dt.strftime("%b")

        day_obj = {
            "date": date_str,
            "level": level,
            "count": count,
            "tooltip": tt if tt else f"{count} contributions on {dt.strftime('%B %d, %Y')}",
            "weekday": weekday,
            "month": month_name,
            "day": dt.day,
            "year": dt.year,
        }
        days.append(day_obj)
        daily_map[date_str] = day_obj

    # Calculate active streak up to today
    today_dt = datetime.now().date()
    today_str = today_dt.strftime("%Y-%m-%d")
    today_count = daily_map.get(today_str, {}).get("count", 0)

    check_dt = today_dt if daily_map.get(today_str, {}).get("count", 0) > 0 else (today_dt - timedelta(days=1))
    while True:
        ds = check_dt.strftime("%Y-%m-%d")
        if ds in daily_map and daily_map[ds].get("count", 0) > 0:
            streak += 1
            check_dt -= timedelta(days=1)
        else:
            break

    # Extract Month Header labels & their week column positions
    # Group days into 53 weeks (columns) x 7 rows
    # A month label is placed on the first column where that month appears and day <= 7
    month_positions = []
    seen_months = set()
    col_idx = 0
    for idx, day in enumerate(days):
        col = idx // 7
        m_key = f"{day['year']}-{day['month']}"
        if m_key not in seen_months and day["day"] <= 14 and col > col_idx:
            seen_months.add(m_key)
            month_positions.append({"month": day["month"], "col": col})
            col_idx = col

    # Group days for the current month
    now = datetime.now()
    cur_year = now.year
    cur_month_str = now.strftime("%b")
    cur_month_days = [d for d in days if d.get("year") == cur_year and d.get("month") == cur_month_str]
    month_total = sum(d.get("count", 0) for d in cur_month_days)

    return {
        "total_contributions": total_count,
        "period_label": period_label,
        "days": days,
        "month_days": cur_month_days,
        "month_total": month_total,
        "month_label": now.strftime("%B %Y"),
        "month_positions": month_positions,
        "today_contributions": today_count,
        "current_streak": streak,
    }


def fetch_github_data(username: str = "", token: str = "") -> Dict[str, Any]:
    """
    Synchronously fetches GitHub profile, calendar grid, events, and stats.
    """
    clean_username = username.strip() if username else ""
    clean_token = token.strip() if token else ""

    if not clean_username and not clean_token:
        return {"error": "Please enter a GitHub Username or Personal Access Token in Settings."}

    headers = {
        "User-Agent": "WidgetsX-GitHubRadar/1.0",
        "Accept": "application/vnd.github.v3+json",
    }
    if clean_token:
        headers["Authorization"] = f"Bearer {clean_token}"

    result: Dict[str, Any] = {
        "username": clean_username,
        "name": clean_username,
        "avatar_url": "",
        "public_repos": 0,
        "followers": 0,
        "total_contributions": 0,
        "period_label": f"in {datetime.now().year}",
        "today_contributions": 0,
        "current_streak": 0,
        "open_prs": 0,
        "days": [],
        "month_positions": [],
        "recent_activity": [],
        "last_synced": datetime.now().strftime("%H:%M"),
        "error": None,
    }

    target_login = clean_username

    # 1. If token provided, resolve user profile
    if clean_token:
        try:
            req = urllib.request.Request("https://api.github.com/user", headers=headers)
            with urllib.request.urlopen(req, timeout=8) as response:
                user_data = json.loads(response.read().decode("utf-8"))
                target_login = user_data.get("login", clean_username)
                result["username"] = target_login
                result["name"] = user_data.get("name") or target_login
                result["avatar_url"] = user_data.get("avatar_url", "")
                result["public_repos"] = user_data.get("public_repos", 0) + user_data.get("total_private_repos", 0)
                result["followers"] = user_data.get("followers", 0)
                result["html_url"] = user_data.get("html_url", f"https://github.com/{target_login}")
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return {"error": "Invalid GitHub Token (401 Unauthorized). Please check your Personal Access Token."}
            logger.warning(f"Failed to query /user: HTTP {e.code}")
        except Exception as e:
            logger.warning(f"Error querying /user: {e}")

    # Fallback to public profile if not yet resolved
    if not result.get("html_url") and target_login:
        try:
            req = urllib.request.Request(f"https://api.github.com/users/{target_login}", headers=headers)
            with urllib.request.urlopen(req, timeout=8) as response:
                user_data = json.loads(response.read().decode("utf-8"))
                target_login = user_data.get("login", target_login)
                result["username"] = target_login
                result["name"] = user_data.get("name") or target_login
                result["avatar_url"] = user_data.get("avatar_url", "")
                result["public_repos"] = user_data.get("public_repos", 0)
                result["followers"] = user_data.get("followers", 0)
                result["html_url"] = user_data.get("html_url", f"https://github.com/{target_login}")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"error": f"GitHub user '{target_login}' was not found."}
            elif e.code == 401:
                return {"error": "Invalid GitHub Token (401 Unauthorized)."}
        except Exception as e:
            logger.warning(f"Error querying /users/{target_login}: {e}")

    if not target_login:
        return {"error": "Could not determine GitHub username."}

    # 2. Fetch Contribution Calendar from HTML endpoint
    calendar_data = fetch_github_calendar_html(target_login)
    if calendar_data and calendar_data.get("days"):
        result["total_contributions"] = calendar_data.get("total_contributions", 0)
        result["period_label"] = calendar_data.get("period_label", f"in {datetime.now().year}")
        result["days"] = calendar_data.get("days", [])
        result["month_days"] = calendar_data.get("month_days", [])
        result["month_total"] = calendar_data.get("month_total", 0)
        result["month_label"] = calendar_data.get("month_label", datetime.now().strftime("%B %Y"))
        result["month_positions"] = calendar_data.get("month_positions", [])
        result["today_contributions"] = calendar_data.get("today_contributions", 0)
        result["current_streak"] = calendar_data.get("current_streak", 0)
    else:
        # Fallback to empty calendar
        empty_days = []
        start_date = datetime.now().date() - timedelta(days=364)
        for i in range(365):
            d = start_date + timedelta(days=i)
            empty_days.append({
                "date": d.strftime("%Y-%m-%d"),
                "level": 0,
                "count": 0,
                "tooltip": f"No contributions on {d.strftime('%B %d, %Y')}",
                "weekday": (d.weekday() + 1) % 7,
                "month": d.strftime("%b"),
                "day": d.day,
                "year": d.year,
            })
        now = datetime.now()
        cur_month_days = [d for d in empty_days if d["year"] == now.year and d["month"] == now.strftime("%b")]
        result["days"] = empty_days
        result["month_days"] = cur_month_days
        result["month_total"] = 0
        result["month_label"] = now.strftime("%B %Y")

    # 3. Query Open PRs count
    try:
        search_pr_url = f"https://api.github.com/search/issues?q=is:pr+author:{target_login}+state:open"
        req = urllib.request.Request(search_pr_url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as response:
            pr_data = json.loads(response.read().decode("utf-8"))
            result["open_prs"] = pr_data.get("total_count", 0)
    except Exception:
        result["open_prs"] = 0

    return result


class GitHubWorker(QThread):
    """Background worker thread for fetching GitHub calendar & stats."""
    data_ready = Signal(dict)

    def __init__(self, username: str, token: str = "", parent=None):
        super().__init__(parent)
        self.username = username
        self.token = token

    def run(self):
        data = fetch_github_data(self.username, self.token)
        self.data_ready.emit(data)


class GitHubAvatarLoader(QThread):
    """Asynchronously fetches user avatar image and emits QPixmap."""
    avatar_loaded = Signal(QPixmap)

    def __init__(self, avatar_url: str, parent=None):
        super().__init__(parent)
        self.avatar_url = avatar_url

    def run(self):
        if not self.avatar_url:
            return
        try:
            req = urllib.request.Request(self.avatar_url, headers={"User-Agent": "WidgetsX-GitHubRadar/1.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                raw_img = resp.read()
                img = QImage.fromData(raw_img)
                if not img.isNull():
                    pix = QPixmap.fromImage(img)
                    self.avatar_loaded.emit(pix)
        except Exception as e:
            logger.debug(f"Failed to load avatar from {self.avatar_url}: {e}")
