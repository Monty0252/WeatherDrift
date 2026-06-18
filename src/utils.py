def average(values):
    return sum(values) / len(values) if values else None

def safe_max(values):
    return max(values) if values else None

def get_values(hourly_data, metric_name):

    values = []
    
    for hour in hourly_data:
        value = hour.get(metric_name)

        if value is not None:
            values.append(float(value))
    return values

def round_value(value, decimals=1):
    if value is None:
        return None
    return round(float(value), decimals)