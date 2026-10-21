"""Read-only object usage audit; not an atomic billing or quota guarantee."""


def measure(client, bucket, prefix, *, max_pages=1000):
    if not isinstance(prefix, str) or not prefix.endswith('/'):
        raise ValueError('invalid_prefix')
    if type(max_pages) is not int or max_pages < 1:
        raise ValueError('invalid_page_limit')
    total = 0
    objects = 0
    token = None
    seen = set()
    for _ in range(max_pages):
        params = {'Bucket': bucket, 'Prefix': prefix, 'MaxKeys': 1000}
        if token is not None:
            params['ContinuationToken'] = token
        page = client.list_objects_v2(**params)
        for obj in page.get('Contents', []):
            size = obj.get('Size')
            if type(size) is not int or size < 0:
                raise ValueError('invalid_object_size')
            total += size
            objects += 1
        if page.get('IsTruncated') is not True:
            return {'used_bytes': total, 'object_count': objects, 'complete': True}
        token = page.get('NextContinuationToken')
        if not isinstance(token, str) or not token or token in seen:
            raise RuntimeError('incomplete_usage_audit')
        seen.add(token)
    raise RuntimeError('usage_audit_page_limit')
