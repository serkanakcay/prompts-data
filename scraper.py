#!/usr/bin/env python3
"""
PromptPlum Scraper & Mobile Data Generator
Downloads prompts and images categorized by library/category from promptplum.com
Outputs structured JSON suitable for mobile apps via GitHub/CDN.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
import argparse

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
BASE_API = "https://api.promptplum.com/api"

def make_request(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except Exception as e:
        print(f"[-] Error fetching {url}: {e}")
        return None

def fetch_json(url):
    data = make_request(url)
    if data:
        try:
            return json.loads(data.decode("utf-8"))
        except Exception as e:
            print(f"[-] JSON decode error for {url}: {e}")
    return None

def get_all_categories():
    """Fetch all libraries/categories from PromptPlum API."""
    print("[*] Fetching category list...")
    categories = []
    page = 1
    while True:
        url = f"{BASE_API}/libraries?page={page}&limit=100"
        res = fetch_json(url)
        if not res or "data" not in res:
            break
        items = res.get("data", [])
        categories.extend(items)
        if page >= res.get("totalPages", 1):
            break
        page += 1
        time.sleep(0.3)
    print(f"[+] Total {len(categories)} categories found.")
    return categories

def download_image(img_url, dest_path):
    """Download image to dest_path if not already downloaded."""
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        return True
    
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    content = make_request(img_url)
    if content:
        with open(dest_path, "wb") as f:
            f.write(content)
        return True
    return False

def scrape_category(category_info, output_dir=".", github_user="user", github_repo="repo", branch="main"):
    """
    Scrape all prompts and images for a specific category.
    """
    cat_id = category_info["_id"]
    cat_name = category_info.get("name", "Unknown")
    cat_slug = category_info.get("slug", "unknown")
    total_count = category_info.get("count", 0)

    print(f"\n==================================================")
    print(f"[*] Processing category: {cat_name} (slug: {cat_slug}, expected: {total_count})")
    print(f"==================================================")

    # Output directories
    images_dir = os.path.join(output_dir, "images", cat_slug)
    data_dir = os.path.join(output_dir, "data")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)

    # Fetch all prompts for this category
    prompts = []
    page = 1
    while True:
        url = f"{BASE_API}/prompts?libraryId={cat_id}&page={page}&limit=100"
        res = fetch_json(url)
        if not res or "data" not in res:
            break
        items = res.get("data", [])
        prompts.extend(items)
        if page >= res.get("totalPages", 1):
            break
        page += 1
        time.sleep(0.3)

    print(f"[+] Fetched {len(prompts)} prompt records from API.")

    processed_prompts = []

    for idx, p in enumerate(prompts):
        pid = p.get("id") or p.get("_id")
        title = p.get("title", "").strip()
        slug = p.get("slug", "")
        meta = p.get("meta", {})
        prompt_text = meta.get("prompt_text", "").strip()
        description = meta.get("description", "").strip()
        ai_tools = [tool.get("name") for tool in p.get("aiTools", []) if isinstance(tool, dict)]
        
        # Images
        result_images = meta.get("result_images", [])
        downloaded_images = []

        for img_idx, img_info in enumerate(result_images):
            original_url = img_info.get("url")
            if not original_url:
                continue
            
            # Filename determination
            filename = os.path.basename(original_url)
            if not filename or "?" in filename:
                ext = ".jpg"
                filename = f"{slug}_{img_idx}{ext}"
            
            local_rel_path = f"images/{cat_slug}/{filename}"
            local_abs_path = os.path.join(output_dir, local_rel_path)

            print(f"    [{idx+1}/{len(prompts)}] Downloading image: {filename}...")
            success = download_image(original_url, local_abs_path)
            
            if success:
                cdn_url = f"https://cdn.jsdelivr.net/gh/{github_user}/{github_repo}@{branch}/{local_rel_path}"
                raw_github_url = f"https://raw.githubusercontent.com/{github_user}/{github_repo}/{branch}/{local_rel_path}"
                downloaded_images.append({
                    "filename": filename,
                    "local_path": local_rel_path,
                    "original_url": original_url,
                    "cdn_url": cdn_url,
                    "raw_github_url": raw_github_url,
                    "width": img_info.get("width"),
                    "height": img_info.get("height"),
                    "alt": img_info.get("alt", "")
                })

        item_data = {
            "id": pid,
            "title": title,
            "slug": slug,
            "category": cat_name,
            "category_slug": cat_slug,
            "prompt": prompt_text,
            "description": description,
            "ai_tools": ai_tools,
            "like_count": p.get("likeCount", 0),
            "view_count": p.get("viewCount", 0),
            "copy_count": p.get("copyCount", 0),
            "is_premium": p.get("isPremium", False),
            "published_at": p.get("publishedAt"),
            "images": downloaded_images
        }
        processed_prompts.append(item_data)

    # Save category JSON
    category_json_file = os.path.join(data_dir, f"{cat_slug}.json")
    category_output = {
        "category": cat_name,
        "slug": cat_slug,
        "total_prompts": len(processed_prompts),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prompts": processed_prompts
    }

    with open(category_json_file, "w", encoding="utf-8") as f:
        json.dump(category_output, f, ensure_ascii=False, indent=2)

    print(f"[+] Saved {len(processed_prompts)} prompts to {category_json_file}")
    return category_output

def main():
    parser = argparse.ArgumentParser(description="PromptPlum Scraper and Mobile Data Builder")
    parser.add_argument("--category", type=str, default="hollywood", help="Specific category slug to scrape (e.g. hollywood)")
    parser.add_argument("--all", action="store_true", help="Scrape all categories")
    parser.add_argument("--list-categories", action="store_true", help="List all available categories")
    parser.add_argument("--output-dir", type=str, default=".", help="Output directory")
    parser.add_argument("--github-user", type=str, default="serkanakcay", help="GitHub username for raw/CDN URLs")
    parser.add_argument("--github-repo", type=str, default="prompts-data", help="GitHub repo name for raw/CDN URLs")
    parser.add_argument("--branch", type=str, default="main", help="Git branch name")
    args = parser.parse_args()

    categories = get_all_categories()

    if args.list_categories:
        print("\nAvailable Categories:")
        for idx, c in enumerate(categories):
            print(f"[{idx+1}] {c.get('name')} (slug: {c.get('slug')}, count: {c.get('count')})")
        return

    # Always save master categories.json for mobile navigation
    data_dir = os.path.join(args.output_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    cats_manifest = [
        {
            "id": c.get("_id"),
            "name": c.get("name"),
            "slug": c.get("slug"),
            "count": c.get("count", 0),
            "api_endpoint": f"data/{c.get('slug')}.json",
            "cdn_url": f"https://cdn.jsdelivr.net/gh/{args.github_user}/{args.github_repo}@{args.branch}/data/{c.get('slug')}.json",
            "raw_url": f"https://raw.githubusercontent.com/{args.github_user}/{args.github_repo}/{args.branch}/data/{c.get('slug')}.json"
        }
        for c in categories
    ]
    with open(os.path.join(data_dir, "categories.json"), "w", encoding="utf-8") as f:
        json.dump({
            "total_categories": len(cats_manifest),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "categories": cats_manifest
        }, f, ensure_ascii=False, indent=2)
    print(f"[+] Saved master categories list to {os.path.join(data_dir, 'categories.json')}")

    if args.all:
        print(f"[*] Scraping ALL {len(categories)} categories...")
        for cat in categories:
            scrape_category(cat, args.output_dir, args.github_user, args.github_repo, args.branch)
            time.sleep(1)
    else:
        target = args.category.lower().strip()
        matched = [c for c in categories if c.get("slug", "").lower() == target or c.get("name", "").lower() == target]
        if not matched:
            print(f"[-] Category '{target}' not found!")
            sys.exit(1)
        scrape_category(matched[0], args.output_dir, args.github_user, args.github_repo, args.branch)

    print("\n[✔] Finished successfully!")

if __name__ == "__main__":
    main()
