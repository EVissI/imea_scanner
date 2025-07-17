import re


def parse_invoice(text: str):
    item_pattern = re.compile(
        r"^(?P<country>[\U0001F1EA-\U0001F1FA\U0001F1E8-\U0001F1F3\U0001F1FA-\U0001F1FF]+)\s+"
        r"(?P<name>.+?)\s+—\s*(?P<price>[\d\s]+,[\d]{2})\s*\((?P<count>\d+)\s*шт\.\)",
        re.MULTILINE,
    )
    items = []
    total_count = 0
    total_sum = 0.0

    for match in item_pattern.finditer(text):
        d = match.groupdict()
        price = float(d["price"].replace(" ", "").replace(" ", "").replace(",", "."))
        count = int(d["count"])
        for i in range(count):
            item = {
                "country": d["country"],  
                "name": d["name"],
                "price": price/count,
            }
            items.append(item)
        total_count += count
        total_sum += price

    count_match = re.search(r"ВСЕГО:\s*(\d+)\s*шт\.", text)
    sum_match = re.search(r"СУММА ТОВАРОВ:\s*([\d\s]+,[\d]{2})", text)

    invoice_count = int(count_match.group(1)) if count_match else None
    invoice_sum = (
        float(sum_match.group(1).replace(" ", "").replace(" ", "").replace(",", "."))
        if sum_match
        else None
    )

    count_ok = invoice_count == total_count
    sum_ok = (abs(invoice_sum - total_sum) < 0.01) if invoice_sum is not None else False

    return {
        "parsed_count": total_count,
        "parsed_sum": total_sum,
        "invoice_count": invoice_count,
        "invoice_sum": invoice_sum,
        "count_ok": count_ok,
        "sum_ok": sum_ok,
        "items": items,
    }


def pop_first(items: list):
    """
    Возвращает первый элемент и новый список без него.
    Если список пуст — возвращает (None, []).
    """
    if not items:
        return None, []
    return items[0], items[1:]


def is_valid_imei(imei: str) -> bool:
    """
    Проверяет IMEI на валидность по алгоритму Луна.
    IMEI должен быть строкой из 15 цифр.
    """
    if not imei.isdigit() or len(imei) != 15:
        return False

    total = 0
    for i, digit in enumerate(imei):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def is_valid_jan(jan: str) -> bool:
    """
    Проверяет JAN (EAN-13) на валидность по контрольной сумме.
    JAN должен быть строкой из 13 цифр.
    """
    if not jan.isdigit() or len(jan) != 13:
        return False

    total = 0
    for i, digit in enumerate(jan[:-1]):
        n = int(digit)
        if i % 2 == 0:
            total += n
        else:
            total += n * 3
    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(jan[-1])
