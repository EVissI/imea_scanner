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


def is_valid_barcode(barcode: str) -> bool:
    """
    Проверяет валидность штрих-кодов EAN-13 (включая JAN), UPC-A, EAN-8 и UPC-E.
    Barcode должен быть строкой из цифр (8, 12 или 13 цифр).
    """
    if not barcode.isdigit():
        return False

    length = len(barcode)

    # Проверка EAN-13 (включая JAN)
    if length == 13:
        total = 0
        for i, digit in enumerate(barcode[:-1]):
            n = int(digit)
            if i % 2 == 0:
                total += n
            else:
                total += n * 3
        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(barcode[-1])

    # Проверка UPC-A
    elif length == 12:
        total = 0
        for i, digit in enumerate(barcode[:-1]):
            n = int(digit)
            if i % 2 == 0:
                total += n * 3
            else:
                total += n
        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(barcode[-1])

    # Проверка EAN-8
    elif length == 8 and not barcode.startswith("0"):  # UPC-E тоже 8 цифр, но начинается с 0
        total = 0
        for i, digit in enumerate(barcode[:-1]):
            n = int(digit)
            if i % 2 == 0:
                total += n * 3
            else:
                total += n
        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(barcode[-1])

    # Проверка UPC-E
    elif length == 8 and barcode.startswith("0"):
        # Преобразование UPC-E в UPC-A
        digits = [int(d) for d in barcode]
        if digits[0] != 0:
            return False
        number_system = digits[0]
        check_digit = digits[7]
        manufacturer_code = digits[1:6]
        
        # Расширение UPC-E до UPC-A
        if digits[6] == 0:
            upc_a = f"{number_system}{barcode[1:3]}0000{barcode[3:6]}{check_digit}"
        elif digits[6] == 1:
            upc_a = f"{number_system}{barcode[1:3]}1000{barcode[3:6]}{check_digit}"
        elif digits[6] == 2:
            upc_a = f"{number_system}{barcode[1:3]}2000{barcode[3:6]}{check_digit}"
        elif digits[6] == 3:
            upc_a = f"{number_system}{barcode[1:4]}000{barcode[4:6]}{check_digit}"
        elif digits[6] == 4:
            upc_a = f"{number_system}{barcode[1:5]}00{barcode[5]}{check_digit}"
        else: 
            upc_a = f"{number_system}{barcode[1:6]}{digits[6]}0000{check_digit}"

        # Проверка UPC-A
        total = 0
        for i, digit in enumerate(upc_a[:-1]):
            n = int(digit)
            if i % 2 == 0:
                total += n * 3
            else:
                total += n
        check_digit = (10 - (total % 10)) % 10
        return check_digit == int(upc_a[-1])

    return False
