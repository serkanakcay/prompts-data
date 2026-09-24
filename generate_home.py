#!/usr/bin/env python3
"""
Home Feed / Dashboard API Generator
Generates data/home.json with:
1. Headline (Manşet): Loads full featured items from the specified category (e.g. Hollywood)
2. Initial Categories (İlk 3 Kategori): Selected categories for the home screen sections
"""

import os
import sys
import json
import argparse

def load_category_data(data_dir, cat_slug):
    filepath = os.path.join(data_dir, f"{cat_slug}.json")
    if not os.path.exists(filepath):
        print(f"[-] Category file not found: {filepath}")
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[-] Error reading {filepath}: {e}")
        return None

def build_home_feed(headline_slug="hollywood", initial_category_slugs=None, data_dir="data", github_user="serkanakcay", github_repo="prompts-data"):
    if initial_category_slugs is None:
        initial_category_slugs = ["portraits", "cinematic", "cyberpunk"]

    print(f"[*] Building home feed with Headline: {headline_slug}")
    print(f"[*] Initial 3 Categories: {initial_category_slugs}")

    # 1. Headline Data
    headline_data = load_category_data(data_dir, headline_slug)
    if not headline_data:
        print(f"[-] Failed to load headline category: {headline_slug}")
        sys.exit(1)

    headline_prompts = headline_data.get("prompts", [])
    
    # 2. Sections / Initial Categories Data
    sections = []
    initial_categories_manifest = []

    for c_slug in initial_category_slugs:
        cat_content = load_category_data(data_dir, c_slug)
        if not cat_content:
            continue
        
        cat_name = cat_content.get("category", c_slug.capitalize())
        all_prompts = cat_content.get("prompts", [])
        
        # Take first 10 items for home feed section preview
        preview_prompts = all_prompts[:10]

        sections.append({
            "category": cat_name,
            "slug": c_slug,
            "total_prompts": len(all_prompts),
            "api_url": f"https://cdn.jsdelivr.net/gh/{github_user}/{github_repo}@main/data/{c_slug}.json",
            "items": preview_prompts
        })

        initial_categories_manifest.append({
            "name": cat_name,
            "slug": c_slug,
            "total_prompts": len(all_prompts),
            "api_url": f"https://cdn.jsdelivr.net/gh/{github_user}/{github_repo}@main/data/{c_slug}.json"
        })

    # 3. Master Home JSON Object
    home_output = {
        "headline_category": headline_slug,
        "updated_at": headline_data.get("updated_at"),
        "headline": {
            "category": headline_data.get("category", "Headline"),
            "slug": headline_slug,
            "total_items": len(headline_prompts),
            "api_url": f"https://cdn.jsdelivr.net/gh/{github_user}/{github_repo}@main/data/{headline_slug}.json",
            "items": headline_prompts
        },
        "initial_categories": initial_categories_manifest,
        "sections": sections
    }

    out_file = os.path.join(data_dir, "home.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(home_output, f, ensure_ascii=False, indent=2)

    print(f"[✔] Successfully generated {out_file}!")
    return home_output

def main():
    parser = argparse.ArgumentParser(description="Generate Home Feed API (data/home.json)")
    parser.add_argument("--headline", type=str, default="hollywood", help="Category slug for headline banner (e.g. hollywood)")
    parser.add_argument("--categories", nargs="+", default=["portraits", "cinematic", "cyberpunk"], help="First 3 category slugs for initial home display")
    parser.add_argument("--data-dir", type=str, default="data", help="Directory containing JSON files")
    args = parser.parse_args()

    build_home_feed(headline_slug=args.headline, initial_category_slugs=args.categories, data_dir=args.data_dir)

if __name__ == "__main__":
    main()
