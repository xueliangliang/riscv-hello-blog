# Manual deployment

Production URL: `https://blog.xueliangliang.dev/`

## Build locally

```sh
npm run check
npm run build
SITE="$(python3 tools/blog.py artifact)" || exit 1
```

The generated site is a fresh `build/release-*/site/`, returned by `artifact` only when source and output hashes still match a successful build. Never deploy an old `public/` or a draft-preview tree. This project is built and published manually; it does not use GitHub Actions. If any command fails, stop rather than continuing with an earlier `SITE` value.

## Publish a new build

The S3 bucket is dedicated to this site. `--delete` removes remote objects not present in the local build, so do not use it if unrelated files are ever added to the bucket.

```sh
aws sts get-caller-identity >/dev/null
aws s3api list-objects-v2 --bucket blog.xueliangliang.dev --query 'Contents[].Key'
SITE="$(python3 tools/blog.py artifact)" || exit 1
aws s3 sync "$SITE/" s3://blog.xueliangliang.dev/ --delete --region ap-southeast-1 --dryrun
# Review the inventory and every planned deletion BEFORE this real upload:
aws s3 sync "$SITE/" s3://blog.xueliangliang.dev/ --delete --region ap-southeast-1
aws cloudfront create-invalidation \
  --distribution-id E1G5X9EHO4H6OU \
  --paths '/*'
```

Record the returned invalidation ID and wait for it with `aws cloudfront wait invalidation-completed --distribution-id E1G5X9EHO4H6OU --id ID`. Read back the exact changed S3 objects and live HTTPS pages, not just the sync exit code. Preserve the private bucket/OAC policy, verify desktop/mobile, comments, analytics and missing-page404 as relevant.

For a new ordered-series chapter, its first production build lists it as pending confirmation. After that article is actually live and the invalidation completed, run `npm run post:confirm -- SLUG`. This performs a fresh build, compares the full live article bytes and updates only its confirmation metadata. Then rebuild, review a new dry run, and manually deploy the now-checked overview. The accepted article bytes must remain unchanged. Homepage, archives, topic lists, feeds and course links are generated; do not edit duplicate lists by hand. The workflow does not touch the separate prototype `BLOG_OUTLINE.md` or certify code/hardware acceptance.

## Google AdSense

The publisher client ID is configured under `[params.adsense]` in `hugo.toml`. The shared head inserts the supplied asynchronous AdSense script once per production content page, with `crossorigin="anonymous"`. Development/staging builds, `hugo server` (even with the production environment selected), and the 404 page omit it. Set `enabled = false` to disable it site-wide.

This installs the site connection script, not a guaranteed ad placement or an account approval. Site review and Auto ads settings remain in the owner's AdSense account. See Google's [code placement guide](https://support.google.com/adsense/answer/9274516?hl=en). No ad units, ads.txt seller authorizations, consent banner, or privacy-policy claims are invented by this change. If the account asks for ads.txt or consent configuration, complete those separately using the actual account settings. For personalized ads to users in the EEA, UK and Switzerland, consult Google's [certified consent-management requirements](https://support.google.com/adsense/answer/13554116?hl=en) before enabling that delivery.

Verify HTML and script attributes without repeatedly requesting live ads or clicking your own ads. Local browser checks block third-party requests. Script installation and the first real ad impression are separate acceptance steps.

## Root domain and canonical routing

`xueliangliang.dev` is an HTTPS entry point, not a second copy of the blog. The existing CloudFront distribution accepts both the root domain and `blog.xueliangliang.dev`; an ACM certificate in `us-east-1` covers both names. Root-domain `A` and `AAAA` aliases point to that distribution. Existing `www` records are unrelated and are not changed by this setup.

The viewer-request function `blog-xueliangliang-dev-canonical-routing`, sourced from `infra/cloudfront-directory-index.js`, returns a 301 from the root domain to `https://blog.xueliangliang.dev` before any directory-index rewriting. It preserves paths and encoded parameter values, sorts query names for deterministic output, and preserves repeated-value order. Redirect responses use a five-minute cache lifetime. HTTP first upgrades to HTTPS through the existing viewer protocol policy; HTTPS then redirects to the canonical blog origin. Blog requests retain the original directory/asset behavior and existing S3 OAC protection.

Run `npm run test:routing` for the Node regression suite; it is also part of `npm run check`. Function changes require separate CloudFront deployment, not an S3 sync: upload to DEVELOPMENT, run native `test-function` events as well as local tests, publish LIVE, then associate using a freshly read distribution ETag. Local JavaScript property enumeration can differ from the CloudFront runtime, so test encoded and repeated query parameters in the actual service. Before creating root DNS aliases, wait for distribution deployment and verify the root hostname against a CloudFront address with normal TLS hostname validation (`curl --resolve`, never `-k`).

Verify public A/AAAA answers, trusted root-domain TLS, the initial 301 and its Location, followed blog HTML containing the intended AdSense publisher ID, blog nested URLs/assets and a real missing-page 404. A working redirect enables crawling; it does not prove that AdSense verification or content review has succeeded. Root `/ads.txt` redirects to blog `/ads.txt`; no ads.txt content is implied or automatically created.

For rollback, the original `blog-xueliangliang-dev-directory-index` function and original blog-only certificate remain available. A routing-only rollback can restore the old function association while keeping the new dual-name certificate. For a complete rollback, remove only the newly created root A/AAAA records, allow DNS caches to expire, and then remove the root alias/restore the original certificate as appropriate. Keep ACM validation CNAMEs for certificate renewal. Use current ETags and preserve unrelated settings; do not blindly overwrite future changes with an old full-distribution snapshot. The initial configuration, validation records and service test receipts are archived locally under ignored `build/apex-redirect/`.

## AWS layout

- S3 bucket: `blog.xueliangliang.dev`, region `ap-southeast-1`.
- The bucket is private, has Block Public Access enabled, and does not use S3 website hosting.
- CloudFront distribution: `E1G5X9EHO4H6OU` (`d2fm8jrgsw0c4t.cloudfront.net`), Price Class 200.
- CloudFront uses Origin Access Control (OAC); the bucket policy grants `s3:GetObject` only to this distribution.
- The active ACM certificate in `us-east-1` covers `xueliangliang.dev` and `blog.xueliangliang.dev`.
- Route 53 `A` and `AAAA` alias records point both root and blog hostnames to CloudFront.
- `infra/cloudfront-directory-index.js` redirects the root domain and maps blog pretty URLs to their `index.html` objects. The distribution returns the generated `/404.html` for missing blog paths.
- The `LL` monogram favicon is in `static/favicon.svg` and is reused in the site header.
- Article comments use giscus with the blog repository's `Announcements` Discussion category and `pathname` mapping; commenters sign in with GitHub.
- Pageviews are measured with Google Analytics 4 (`gtag.js`). The measurement ID lives in `hugo.toml` under `[services.googleAnalytics]` and is rendered by `layouts/_default/baseof.html`; the tag appears once in every page head, including `404.html`. GA4 sets its own cookies, so add a disclosure or consent step if you need one for your audience.

Do not make the S3 bucket public or change the CloudFront origin to the S3 website endpoint; that would bypass the current OAC setup.
