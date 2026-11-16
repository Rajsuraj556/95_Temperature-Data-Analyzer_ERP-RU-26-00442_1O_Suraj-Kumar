import csv
import math
import statistics
from html import escape
from pathlib import Path


def load_data():
    """Load and validate temperature data from the CSV file."""
    csv_path = Path(__file__).resolve().parent / "temps.csv"

    try:
        with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)

            if reader.fieldnames is None:
                print("Error: CSV file is empty.")
                return []

            field_names = reader.fieldnames
            date_field = "Date" if "Date" in field_names else "Data" if "Data" in field_names else None
            if date_field is None:
                print("Error: CSV must contain Date (or legacy Data) and Temp_C columns.")
                return []

            if "Temp_C" not in field_names:
                print("Error: CSV must contain Temp_C column.")
                return []

            valid_rows = []
            for row in reader:
                date = (row.get(date_field) or "").strip()
                raw_temp = (row.get("Temp_C") or "").strip()

                try:
                    temperature = float(raw_temp)
                    if not math.isfinite(temperature):
                        raise ValueError
                except ValueError:
                    print(f"Invalid reading '{raw_temp}' on {date}. Value ignored (NaN).")
                    continue

                valid_rows.append({"Date": date, "Temp_C": temperature})

            if not valid_rows:
                print("No valid temperature data found.")
                return []

            return valid_rows

    except FileNotFoundError:
        print(f"Error: {csv_path.name} file not found.")
        return []
    except OSError as exc:
        print(f"Error: {exc}")
        return []


def calculate_statistics(rows):
    """Calculate mean, median, min, max, and standard deviation."""
    temperatures = [row["Temp_C"] for row in rows]

    mean = statistics.fmean(temperatures)
    median = statistics.median(temperatures)
    maximum = max(temperatures)
    minimum = min(temperatures)
    std_dev = statistics.pstdev(temperatures) if len(temperatures) > 1 else 0.0

    print("\n----- Temperature Statistics -----")
    print(f"Mean: {mean:.2f}")
    print(f"Median: {median:.2f}")
    print(f"Maximum: {maximum:.2f}")
    print(f"Minimum: {minimum:.2f}")
    print(f"Std Dev: {std_dev:.2f}")

    hot_days = [row["Date"] for row in rows if row["Temp_C"] > 35]
    print("\nHot Days (Above 35 C):")
    if not hot_days:
        print("No days above 35 C")
    else:
        for date in hot_days:
            print(date)


def save_svg(filename, contents):
    """Write a chart as a dependency-free SVG file."""
    output_path = Path(__file__).resolve().parent / filename
    try:
        output_path.write_text(contents, encoding="utf-8")
    except OSError as exc:
        print(f"Could not save chart to {output_path}: {exc}")
        return
    print(f"Chart saved to {output_path}")


def make_svg_start(title, width, height):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width / 2}" y="30" text-anchor="middle" '
        f'font-family="Arial, sans-serif" font-size="20">{escape(title)}</text>',
    ]


def make_line_chart(rows, column, unit):
    width, height = 900, 520
    left, right, top, bottom = 85, 30, 55, 145
    plot_width = width - left - right
    plot_height = height - top - bottom
    values = [row[column] for row in rows]
    low, high = min(values), max(values)
    if low == high:
        low -= 1
        high += 1
    else:
        padding = (high - low) * 0.1
        low -= padding
        high += padding

    def x_position(index):
        if len(values) == 1:
            return left + plot_width / 2
        return left + index * plot_width / (len(values) - 1)

    def y_position(value):
        return top + (high - value) * plot_height / (high - low)

    parts = make_svg_start(f"Temperature Trend ({unit})", width, height)
    for tick in range(6):
        value = low + (high - low) * tick / 5
        y = y_position(value)
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" '
            'stroke="#dddddd"/>'
        )
        parts.append(
            f'<text x="{left - 10}" y="{y + 5:.1f}" text-anchor="end" '
            f'font-family="Arial, sans-serif" font-size="12">{value:.1f}</text>'
        )

    points = " ".join(
        f"{x_position(index):.1f},{y_position(value):.1f}"
        for index, value in enumerate(values)
    )
    parts.append(
        f'<polyline points="{points}" fill="none" stroke="#2474b5" stroke-width="3"/>'
    )
    for index, row in enumerate(rows):
        x = x_position(index)
        y = y_position(row[column])
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#2474b5"/>')
        parts.append(
            f'<text x="{x:.1f}" y="{height - bottom + 22}" '
            f'transform="rotate(-45 {x:.1f} {height - bottom + 22})" '
            f'font-family="Arial, sans-serif" font-size="11">{escape(row["Date"])}</text>'
        )
    parts.extend([
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" stroke="#333"/>',
        f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" '
        f'y2="{height - bottom}" stroke="#333"/>',
        f'<text x="20" y="{height / 2}" text-anchor="middle" '
        f'transform="rotate(-90 20 {height / 2})" '
        f'font-family="Arial, sans-serif" font-size="14">Temperature ({escape(unit)})</text>',
        "</svg>",
    ])
    return "\n".join(parts)


def make_histogram(values, unit):
    width, height = 800, 500
    left, right, top, bottom = 75, 30, 55, 75
    plot_width = width - left - right
    plot_height = height - top - bottom
    low, high = min(values), max(values)
    if low == high:
        low -= 0.5
        high += 0.5

    bin_count = min(5, len(values))
    bin_width = (high - low) / bin_count
    counts = [0] * bin_count
    for value in values:
        index = min(int((value - low) / bin_width), bin_count - 1)
        counts[index] += 1
    max_count = max(counts)

    parts = make_svg_start(f"Temperature Histogram ({unit})", width, height)
    for tick in range(max_count + 1):
        y = top + plot_height - tick * plot_height / max_count
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" '
            'stroke="#dddddd"/>'
        )
        parts.append(
            f'<text x="{left - 10}" y="{y + 5:.1f}" text-anchor="end" '
            f'font-family="Arial, sans-serif" font-size="12">{tick}</text>'
        )

    bar_width = plot_width / bin_count
    for index, count in enumerate(counts):
        bar_height = count * plot_height / max_count
        x = left + index * bar_width
        y = top + plot_height - bar_height
        parts.append(
            f'<rect x="{x + 2:.1f}" y="{y:.1f}" width="{max(0, bar_width - 4):.1f}" '
            f'height="{bar_height:.1f}" fill="#55a868"/>'
        )
        parts.append(
            f'<text x="{x + bar_width / 2:.1f}" y="{height - bottom + 22}" '
            f'text-anchor="middle" font-family="Arial, sans-serif" font-size="11">'
            f'{low + index * bin_width:.1f} - {low + (index + 1) * bin_width:.1f}</text>'
        )
    parts.extend([
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height - bottom}" stroke="#333"/>',
        f'<line x1="{left}" y1="{height - bottom}" x2="{width - right}" '
        f'y2="{height - bottom}" stroke="#333"/>',
        f'<text x="{width / 2}" y="{height - 15}" text-anchor="middle" '
        f'font-family="Arial, sans-serif" font-size="14">Temperature ({escape(unit)})</text>',
        "</svg>",
    ])
    return "\n".join(parts)


def plot_graph(rows, column, unit):
    """Save a temperature line chart and histogram without external packages."""
    temperatures = [row[column] for row in rows]
    save_svg(f"temperature_trend_{unit}.svg", make_line_chart(rows, column, unit))
    save_svg(
        f"temperature_histogram_{unit}.svg",
        make_histogram(temperatures, unit),
    )


def convert_to_fahrenheit(rows):
    """Convert temperatures to Fahrenheit and print them."""
    converted = []
    for row in rows:
        converted.append({
            "Date": row["Date"],
            "Temp_F": (row["Temp_C"] * 9 / 5) + 32,
        })

    print("\n----- Fahrenheit Temperature -----")
    for row in converted:
        print(f"{row['Date']}: {row['Temp_F']:.2f} F")

    plot_graph(converted, "Temp_F", "F")


def main():
    rows = load_data()
    if not rows:
        return

    while True:
        print("\n===== TEMPERATURE DATA ANALYZER =====")
        print("1. Calculate Temperature Statistics")
        print("2. Plot Temperature Graphs (Celsius)")
        print("3. Convert to Fahrenheit and Plot")
        print("0. Exit")

        choice = input("\nEnter your choice: ")

        if choice == "1":
            calculate_statistics(rows)
        elif choice == "2":
            plot_graph(rows, "Temp_C", "C")
        elif choice == "3":
            convert_to_fahrenheit(rows)
        elif choice == "0":
            print("Thank you for using Temperature Data Analyzer!")
            break
        else:
            print("Invalid choice! Please try again.")


if __name__ == "__main__":
    main()