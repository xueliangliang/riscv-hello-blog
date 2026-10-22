# Manual deployment

Production URL: `https://blog.xueliangliang.dev/`

## Build locally

```sh
hugo --minify
```

The generated site is in `public/`. This project is built and published manually; it does not use GitHub Actions.

## Publish a new build

The S3 bucket is dedicated to this site. `--delete` removes remote objects not present in the local build, so do not use it if unrelated files are ever added to the bucket.

```sh
aws s3 sync public/ s3://blog.xueliangliang.dev/ --delete --region ap-southeast-1
aws cloudfront create-invalidation \
  --distribution-id E1G5X9EHO4H6OU \
  --paths '/*'
```

The initial upload is already present in S3. For later changes, run the build, sync, then invalidate CloudFront so cached HTML and CSS refresh.

## AWS layout

- S3 bucket: `blog.xueliangliang.dev`, region `ap-southeast-1`.
- The bucket is private, has Block Public Access enabled, and does not use S3 website hosting.
- CloudFront distribution: `E1G5X9EHO4H6OU` (`d2fm8jrgsw0c4t.cloudfront.net`), Price Class 200.
- CloudFront uses Origin Access Control (OAC); the bucket policy grants `s3:GetObject` only to this distribution.
- ACM certificate for `blog.xueliangliang.dev` is in `us-east-1`.
- Route 53 `A` and `AAAA` alias records point `blog.xueliangliang.dev` to CloudFront.
- `infra/cloudfront-directory-index.js` maps Hugo pretty URLs to their `index.html` objects. The distribution returns the generated `/404.html` for missing paths.

Do not make the S3 bucket public or change the CloudFront origin to the S3 website endpoint; that would bypass the current OAC setup.
