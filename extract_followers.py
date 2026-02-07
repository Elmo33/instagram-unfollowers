import argparse
import json
import re
from pathlib import Path


PROFILE_HREF_RE = re.compile(r'href="/([^"/\s]+)/"')

# Common non-profile routes (keep this small; add more if you see false positives)
RESERVED_PATHS = {
    "accounts",
    "about",
    "explore",
    "direct",
    "p",
    "reel",
    "reels",
    "stories",
    "privacy",
    "terms",
}


def extract_usernames(html: str) -> list[str]:
    seen: dict[str, None] = {}
    for m in PROFILE_HREF_RE.finditer(html):
        username = m.group(1).strip()
        if not username:
            continue
        if username in RESERVED_PATHS:
            continue
        # Heuristic: Instagram usernames are typically [A-Za-z0-9._]
        # Keep it permissive to avoid missing anything in your export.
        if not re.fullmatch(r"[A-Za-z0-9._]{1,64}", username):
            continue
        seen.setdefault(username, None)
    return list(seen.keys())


def extract_usernames_from_file(path: Path) -> list[str]:
    if not path.exists():
        return []
    if path.stat().st_size == 0:
        return []
    html = path.read_text(encoding="utf-8", errors="ignore")
    return extract_usernames(html)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract Instagram followers and following usernames from HTML exports"
    )
    parser.add_argument(
        "--followers",
        default="followers.html",
        help="Path to followers.html (default: followers.html)",
    )
    parser.add_argument(
        "--following",
        default="following.html",
        help="Path to following.html (default: following.html)",
    )
    parser.add_argument(
        "--sort",
        action="store_true",
        help="Sort usernames alphabetically (default: keep file order from HTML)",
    )
    parser.add_argument(
        "--out",
        default="",
        help="Output basename (default: writes followers.json and following.json; if set, writes <out>_followers.json and <out>_following.json)",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Also write a comparison JSON (mutuals, not-following-back, not-followed-back).",
    )
    args = parser.parse_args()

    followers_path = Path(args.followers)
    following_path = Path(args.following)

    followers = extract_usernames_from_file(followers_path)
    following = extract_usernames_from_file(following_path)

    if args.sort:
        followers.sort(key=str.lower)
        following.sort(key=str.lower)

    if args.out:
        followers_json_path = Path(f"{args.out}_followers.json")
        following_json_path = Path(f"{args.out}_following.json")
    else:
        followers_json_path = Path("followers.json")
        following_json_path = Path("following.json")

    followers_payload = {
        "count": len(followers),
        "usernames": followers,
    }
    following_payload = {
        "count": len(following),
        "usernames": following,
    }

    followers_json_path.write_text(
        json.dumps(followers_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    following_json_path.write_text(
        json.dumps(following_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Followers: {len(followers)} -> {followers_json_path}")
    print(f"Following: {len(following)} -> {following_json_path}")

    if args.compare:
        def norm(u: str) -> str:
            return u.lower()

        followers_norm = {norm(u) for u in followers}
        following_norm = {norm(u) for u in following}

        # Preserve stable order from the source lists
        mutual = [u for u in followers if norm(u) in following_norm]
        not_following_back = [u for u in following if norm(u) not in followers_norm]
        not_followed_back = [u for u in followers if norm(u) not in following_norm]

        if args.sort:
            mutual.sort(key=str.lower)
            not_following_back.sort(key=str.lower)
            not_followed_back.sort(key=str.lower)

        if args.out:
            comparison_json_path = Path(f"{args.out}_comparison.json")
        else:
            comparison_json_path = Path("comparison.json")

        comparison_payload = {
            "followers_count": len(followers),
            "following_count": len(following),
            "mutual_count": len(mutual),
            "not_following_back_count": len(not_following_back),
            "not_followed_back_count": len(not_followed_back),
            "mutual": mutual,
            "not_following_back": not_following_back,
            "not_followed_back": not_followed_back,
        }

        comparison_json_path.write_text(
            json.dumps(comparison_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        print(f"Comparison -> {comparison_json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

