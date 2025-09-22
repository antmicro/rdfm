def upload_part_count(upload_size: int, desired_part_size: int) -> tuple[int, int]:
    """Returns part count and part size for given upload size"""
    # limits based on
    # https://docs.aws.amazon.com/en_us/AmazonS3/latest/userguide/qfacts.html
    MIN_PART_SIZE = 5 * 2**20  # last part has no minimum size limit
    MAX_PART_SIZE = 5 * 2**30
    MAX_PART_COUNT = 10000
    MAX_UPLOAD_SIZE = 5 * 2**40

    if desired_part_size < MIN_PART_SIZE:
        desired_part_size = MIN_PART_SIZE
    if desired_part_size > MAX_PART_SIZE:
        desired_part_size = MAX_PART_SIZE

    def int_div_ceil(a, b):
        return (a + b - 1) // b

    if upload_size > MAX_UPLOAD_SIZE:
        raise Exception("File is too large to upload")

    if upload_size <= desired_part_size:
        return 1, upload_size

    count = int_div_ceil(upload_size, desired_part_size)
    if count <= MAX_PART_COUNT:
        return count, desired_part_size

    return MAX_PART_COUNT, int_div_ceil(upload_size, MAX_PART_COUNT)
