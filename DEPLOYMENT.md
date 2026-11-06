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

## AWS layout

- S3 bucket: `blog.xueliangliang.dev`, region `ap-southeast-1`.
- The bucket is private, has Block Public Access enabled, and does not use S3 website hosting.
- CloudFront distribution: `E1G5X9EHO4H6OU` (`d2fm8jrgsw0c4t.cloudfront.net`), Price Class 200.
- CloudFront uses Origin Access Control (OAC); the bucket policy grants `s3:GetObject` only to this distribution.
- ACM certificate for `blog.xueliangliang.dev` is in `us-east-1`.
- Route 53 `A` and `AAAA` alias records point `blog.xueliangliang.dev` to CloudFront.
- `infra/cloudfront-directory-index.js` maps Hugo pretty URLs to their `index.html` objects. The distribution returns the generated `/404.html` for missing paths.
- The `LL` monogram favicon is in `static/favicon.svg` and is reused in the site header.
- Article comments use giscus with the blog repository's `Announcements` Discussion category and `pathname` mapping; commenters sign in with GitHub.
- Pageviews are measured with Google Analytics 4 (`gtag.js`). The measurement ID lives in `hugo.toml` under `[services.googleAnalytics]` and is rendered by `layouts/_default/baseof.html`; the tag appears once in every page head, including `404.html`. GA4 sets its own cookies, so add a disclosure or consent step if you need one for your audience.

Do not make the S3 bucket public or change the CloudFront origin to the S3 website endpoint; that would bypass the current OAC setup.
