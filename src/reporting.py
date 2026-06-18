import csv

def create_csv_report(reports , output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        writer.writerow(
            [
                "Location",
                "Date",
                "Metric",
                "Source A",
                "Source B",
                "Source A Value",
                "Source B Value",
                "Difference",
                "Status",
            ]
        )

        for report in reports:
            for metric in report.metrics:
                writer.writerow(
                    [
                        report.location_code,
                        report.weather_date,
                        metric.metric,
                        report.source_a,
                        report.source_b,
                        metric.source_a_value,
                        metric.source_b_value,
                        metric.diff,
                        metric.status,
                    ]
                )