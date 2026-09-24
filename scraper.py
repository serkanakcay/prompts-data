#!/usr/bin/env python3
"""
PromptPlum Full Scraper & GitHub API Sync
Downloads all 300+ categories, prompts, and images with multi-threading,
generates clean mobile JSON files, and pushes to GitHub.
"""

import os
import sys
import json
import time
import shutil
import urllib.request
import urllib.error
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
BASE_API = "https://api.promptplum.com/api"

# Global image cache to avoid re-downloading identical images across categories
IMAGE_CACHE = {}

def make_request(url, retries=3, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            if attempt < retries:
                time.sleep(1 * attempt)
            else:
                print(f"[-] Failed to fetch {url} after {retries} attempts: {e}")
                return None

def fetch_json(url, retries=3):
    data = make_request(url, retries=retries)
    if data:
        try:
            return json.loads(data.decode("utf-8"))
        except Exception as e:
            print(f"[-] JSON decode error for {url}: {e}")
    return None

def get_all_categories():
    """Fetch all libraries/categories from PromptPlum API."""
    print("[*] Fetching category list from PromptPlum...")
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
        time.sleep(0.2)
    print(f"[+] Total {len(categories)} categories found.")
    return categories

def download_image_task(img_url, dest_path):
    """Worker task to download an image with local caching."""
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        return True
    
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    # Check if we already have this image in another category
    if img_url in IMAGE_CACHE and os.path.exists(IMAGE_CACHE[img_url]):
        try:
            shutil.copyfile(IMAGE_CACHE[img_url], dest_path)
            return True
        except:
            pass

    content = make_request(img_url, retries=3, timeout=20)
    if content and len(content) > 0:
        with open(dest_path, "wb") as f:
            f.write(content)
        IMAGE_CACHE[img_url] = dest_path
        return True
    return False

def scrape_category(category_info, output_dir=".", github_user="serkanakcay", github_repo="prompts-data", branch="main"):
    cat_id = category_info["_id"]
    cat_name = category_info.get("name", "Unknown").strip()
    cat_slug = category_info.get("slug", "unknown").strip()
    total_count = category_info.get("count", 0)

    images_dir = os.path.join(output_dir, "images", cat_slug)
    data_dir = os.path.join(output_dir, "data")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)

    category_json_file = os.path.join(data_dir, f"{cat_slug}.json")

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
        time.sleep(0.2)

    # Collect images to download in parallel
    download_tasks = []
    processed_prompts = []

    for idx, p in enumerate(prompts):
        pid = p.get("id") or p.get("_id")
        title = p.get("title", "").strip()
        slug = p.get("slug", "").strip()
        meta = p.get("meta", {})
        prompt_text = meta.get("prompt_text", "").strip()
        description = meta.get("description", "").strip()
        ai_tools = [tool.get("name") for tool in p.get("aiTools", []) if isinstance(tool, dict)]
        
        result_images = meta.get("result_images", [])
        prompt_image_records = []

        for img_idx, img_info in enumerate(result_images):
            original_url = img_info.get("url")
            if not original_url:
                continue
            
            filename = os.path.basename(original_url)
            if not filename or "?" in filename:
                filename = f"{slug}_{img_idx}.jpg"
            
            local_rel_path = f"images/{cat_slug}/{filename}"
            local_abs_path = os.path.join(output_dir, local_rel_path)

            download_tasks.append((original_url, local_abs_path))

            cdn_url = f"https://cdn.jsdelivr.net/gh/{github_user}/{github_repo}@{branch}/{local_rel_path}"
            raw_github_url = f"https://raw.githubusercontent.com/{github_user}/{github_repo}/{branch}/{local_rel_path}"

            prompt_image_records.append({
                "filename": filename,
                "local_path": local_rel_path,
                "original_url": original_url,
                "cdn_url": cdn_url,
                "raw_github_url": raw_github_url,
                "width": img_info.get("width"),
                "height": img_info.get("height"),
                "alt": img_info.get("alt", "")
            })

        processed_prompts.append({
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
            "images": prompt_image_records
        })

    # Download images using ThreadPoolExecutor for high speed
    if download_tasks:
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(download_image_task, url, path) for url, path in download_tasks]
            for _ in as_completed(futures):
                pass

    # Save category JSON
    category_output = {
        "category": cat_name,
        "slug": cat_slug,
        "total_prompts": len(processed_prompts),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prompts": processed_prompts
    }

    with open(category_json_file, "w", encoding="utf-8") as f:
        json.dump(category_output, f, ensure_ascii=False, indent=2)

    return len(processed_prompts), len(download_tasks)

def git_commit_and_push(batch_msg):
    """Commit current changes and push to GitHub."""
    print(f"\n[*] Committing and pushing to GitHub: {batch_msg}...")
    try:
        os.system("git add data/ images/")
        status = os.system(f'git commit -m "{batch_msg}"')
        if status == 0:
            push_res = os.system("git push origin main")
            if push_res == 0:
                print("[✔] Successfully pushed to GitHub!")
            else:
                print("[-] Push failed, will retry later.")
        else:
            print("[*] Nothing new to commit.")
    except Exception as e:
        print(f"[-] Git error: {e}")

def main():
    parser = argparse.ArgumentParser(description="PromptPlum Scraper and Mobile Data Builder")
    parser.add_argument("--category", type=str, default=None, help="Specific category slug to scrape")
    parser.add_argument("--all", action="store_true", help="Scrape all categories")
    parser.add_argument("--output-dir", type=str, default=".", help="Output directory")
    parser.add_argument("--github-user", type=str, default="serkanakcay", help="GitHub username")
    parser.add_argument("--github-repo", type=str, default="prompts-data", help="GitHub repo name")
    parser.add_argument("--branch", type=str, default="main", help="Git branch name")
    args = parser.parse_args()

    categories = get_all_categories()

    # Pre-populate IMAGE_CACHE with existing images
    images_base = os.path.join(args.output_dir, "images")
    if os.path.exists(images_base):
        for root, _, files in os.walk(images_base):
            for file in files:
                full_p = os.path.join(root, file)
                # Map filename
                IMAGE_CACHE[file] = full_p

    # Master categories.json
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

    if args.category:
        target = args.category.lower().strip()
        matched = [c for c in categories if c.get("slug", "").lower() == target or c.get("name", "").lower() == target]
        if not matched:
            print(f"[-] Category '{target}' not found!")
            sys.exit(1)
        p_count, img_count = scrape_category(matched[0], args.output_dir, args.github_user, args.github_repo, args.branch)
        print(f"[✔] Done. Prompts: {p_count}, Images: {img_count}")
        git_commit_and_push(f"feat: add category {matched[0].get('slug')}")
        return

    # Process all categories
    total_cats = len(categories)
    print(f"\n[*] Starting full scrape of {total_cats} categories...")

    total_prompts_all = 0
    total_images_all = 0

    for idx, cat in enumerate(categories):
        cat_name = cat.get("name")
        cat_slug = cat.get("slug")
        cat_json_path = os.path.join(data_dir, f"{cat_slug}.json")
        if os.path.exists(cat_json_path) and os.path.getsize(cat_json_path) > 50:
            print(f"[{idx+1}/{total_cats}] ⏩ Already scraped {cat_name} ({cat_slug}), skipping...")
            continue

        p_count, img_count = scrape_category(cat, args.output_dir, args.github_user, args.github_repo, args.branch)
        total_prompts_all += p_count
        total_images_all += img_count

        print(f"[{idx+1}/{total_cats}] ✔ {cat_name} ({cat_slug}): {p_count} prompts, {img_count} images.")

        # Batch push every 15 categories to keep git commits reasonable and safe
        if (idx + 1) % 15 == 0:
            git_commit_and_push(f"feat: sync categories batch up to {idx+1}/{total_cats}")

    # Final git commit & push
    git_commit_and_push("feat: full sync of all categories and prompt images completed")
    print(f"\n[🎉] FULL SCRAPE COMPLETE! Total Prompts: {total_prompts_all}, Total Images: {total_images_all}")

if __name__ == "__main__":
    main()
