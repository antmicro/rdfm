from pathlib import Path
from collections import defaultdict


def parse_file(data: dict[str, dict[int, list[float]]], file: Path) -> dict:
    """Reads `file` and appends time measurements to `data`."""
    with file.open("r") as fd:
        for line in fd:
            _, url, resp, time = line.rsplit(" ", maxsplit=3)
            data[url][resp].append(float(time))
    return data


def metrics(times: list[float]) -> tuple[float, ...]:
    """Calculates metrics from `times`.

    Args:
        times: List of floats

    Returns:
        average, min, med, max, sum
    """
    s = sum(times)
    n = len(times)
    sort_times = sorted(times)
    return (
        s / n,
        min(times),
        sort_times[n // 2]
        if n % 2 == 1
        else (sort_times[n // 2] + sort_times[n // 2 + 1]) / 2,
        max(times),
        s,
    )


def parse(files: list[Path]) -> dict[str, dict[int, dict]]:
    """Parses `files` and returns dictionary
    with time measurements and calculated metrics.
    """
    data = defaultdict(lambda: defaultdict(list))
    for file in files:
        data = parse_file(data, file)
    for url, results in data.items():
        print(url)
        for response, times in results.items():
            print(f"\t{response}:")
            m = metrics(times)
            print(
                f"\t avg={m[0]:.3f}s min={m[1]:.3f}s med={m[2]:.3f}s max={m[3]:.3f}s sum={m[4]:.3f}s"
            )
            results[response] = {
                "times": times,
                "avg": m[0],
                "min": m[1],
                "med": m[2],
                "max": m[3],
                "sum": m[4],
            }
    return data
