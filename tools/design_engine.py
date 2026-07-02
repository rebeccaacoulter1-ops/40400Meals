from datetime import datetime


def get_seasonal_template(month):
    seasonal_templates = {
        1: "P01 Classic Recipe v1.0",
        2: "P11 Valentine's",
        3: "P01 Classic Recipe v1.0",
        4: "P12 Easter",
        5: "P05 Spring",
        6: "P06 Summer",
        7: "P06 Summer",
        8: "P01 Classic Recipe v1.0",
        9: "P07 Fall",
        10: "P08 Halloween",
        11: "P09 Thanksgiving",
        12: "P10 Christmas",
    }

    return seasonal_templates.get(month, "P01 Classic Recipe v1.0")


def choose_template(platform="pinterest", recipe_category="general"):
    today = datetime.now()
    month = today.month

    if platform == "pinterest":
        template = get_seasonal_template(month)
    else:
        template = "P01 Classic Recipe v1.0"

    return {
        "platform": platform,
        "template_name": template,
        "template_type": "seasonal" if template != "P01 Classic Recipe v1.0" else "evergreen",
        "month": month,
        "recipe_category": recipe_category,
        "version": "1.0"
    }


if __name__ == "__main__":
    selected = choose_template()
    print("Bear OS Design Engine selected:")
    print(selected)
