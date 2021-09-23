from typing import Generator, Any
from dataclasses import dataclass

_address_fias_info = {
    0: {0: ("-", "Не выбрано")},
    1: {
        1: ("стр", "Страна"),
        101: ("АО", "Автономный округ"),
        102: ("Аобл", "Автономная область"),
        103: ("г", "Город"),
        104: ("край", "Край"),
        105: ("обл", "Область"),
        106: ("Респ", "Республика"),
        107: ("округ", "Округ"),
        108: ("Чувашия", "Чувашия"),
        109: ("а.обл.", "Автономная область"),
        110: ("а.окр.", "Автономный округ"),
        111: ("г.", "Город"),
        112: ("г.ф.з.", "Город федерального значения"),
        113: ("обл.", "Область"),
        114: ("респ.", "Республика"),
    },
    2: {
        201: ("АО", "Автономный округ")
    },
    3: {
        301: ("р-н", "Район"),
        302: ("у", "Улус"),
        303: ("тер", "Территория"),
        305: ("АО", "Автономный округ"),
        306: ("п", "Поселение"),
        307: ("вн.тер. г.", "Внутригородская территория"),
        308: ("г.о.", "Городской округ"),
        309: ("м.р-н", "Муниципальный район"),
        310: ("пос.", "Поселение"),
        311: ("у.", "Улус"),
    },
    35: {
        3501: ("вн.р-н", "Внутригородской район"),
        3502: ("г. п.", "Городское поселение"),
        3503: ("с.п.", "Сельское поселение"),
        3504: ("с/с", "Сельсовет"),
    },
    4: {
        401: ("г", "Город"),
        402: ("пгт", "посёлок городского типа"),
        403: ("рп", "Рабочий посёлок"),
        404: ("кп", "Курортный посёлок"),
        405: ("дп", "Дачный посёлок"),
        406: ("с/с", "Сельсовет"),
        407: ("с/а", "Сельская администрация"),
        409: ("с/о", "Сельский округ"),
        410: ("волость", "Волость"),
        411: ("п/о", "Почтовое отделение"),
        412: ("тер", "Территория"),
        414: ("с/п", "Сельское поселение"),
        415: ("с/мо", "Сельское муницип.образование"),
        416: ("массив", "Массив"),
        417: ("п", "посёлок"),
        418: ("г.", "Город"),
        419: ("пгт.", "посёлок городского типа"),
    },
    5: {
        502: ("тер", "Территория"),
        503: ("р-н", "Район"),
    },
    6: {
        601: ("аал", "Аал"),
        602: ("аул", "Аул"),
        603: ("волость", "Волость"),
        604: ("высел", "Выселки(ок)"),
        605: ("г", "Город"),
        606: ("д", "Деревня"),
        607: ("дп", "Дачный посёлок"),
        608: ("ж/д_будка", "Железнодорожная будка"),
        609: ("ж/д_казарм", "Железнодорожная казарма"),
        610: ("ж/д_оп", "ж/д останов. (обгонный) пункт"),
        611: ("ж/д_пост", "Железнодорожный пост"),
        612: ("ж/д_рзд", "Железнодорожный разъезд"),
        613: ("ж/д_ст", "Железнодорожная станция"),
        614: ("заимка", "Заимка"),
        615: ("казарма", "Казарма"),
        616: ("кп", "Курортный посёлок"),
        617: ("м", "Местечко"),
        618: ("мкр", "Микрорайон"),
        619: ("нп", "Населённый пункт"),
        620: ("остров", "Остров"),
        621: ("п", "посёлок"),
        622: ("п/р", "Планировочный район"),
        623: ("п/ст", "посёлок и(при) станция(и)"),
        624: ("пгт", "посёлок городского типа"),
        625: ("починок", "Починок"),
        626: ("п/о", "Почтовое отделение"),
        627: ("промзона", "Промышленная зона"),
        628: ("рзд", "Разъезд"),
        629: ("рп", "Рабочий посёлок"),
        630: ("с", "Село"),
        631: ("сл", "Слобода"),
        632: ("ст", "Станция"),
        633: ("ст-ца", "Станица"),
        634: ("у", "Улус"),
        635: ("х", "Хутор"),
        636: ("г-к", "Городок"),
        637: ("тер", "Территория"),
        638: ("ж/д_платф", "Железнодорожная платформа"),
        639: ("кв-л", "Квартал"),
        640: ("арбан", "Арбан"),
        641: ("снт", "Садовое неком-е товарищество"),
        642: ("лпх", "Леспромхоз"),
        643: ("погост", "Погост"),
        644: ("кордон", "Кордон"),
        645: ("автодорога", "Автодорога"),
        646: ("жилрайон", "Жилой район"),
        647: ("жилзона", "Жилая зона"),
        648: ("массив", "Массив"),
        649: ("гп", "Городской посёлок"),
        650: ("ж/д б-ка", "Железнодорожная будка"),
        651: ("пгт.", "посёлок городского типа"),
        652: ("ж/д пл-ка", "Железнодорожная площадка"),
        653: ("ж/д пл-ма", "Железнодорожная платформа"),
        654: ("киш.", "Кишлак"),
        655: ("п. ж/д ст.", "посёлок при железнодорожной станции"),
        656: ("ж/д бл-ст", "Железнодорожный блокпост"),
        657: ("ж/д в-ка", "Железнодорожная ветка"),
        658: ("ж/д к-ма", "Железнодорожная казарма"),
        659: ("ж/д к-т", "Железнодорожный комбинат"),
        660: ("ж/д п.п.", "Железнодорожный путевой пост"),
        661: ("ж/д о.п.", "Железнодорожный остановочный пункт"),
        662: ("зим.", "Зимовье"),
        663: ("нп.", "Населённый пункт"),
        664: ("дп.", "Дачный посёлок"),
        665: ("сп.", "Сельский посёлок"),
        666: ("пос.рзд", "посёлок разъезда"),
        667: ("сп", "Сельский посёлок"),
    },
    65: {
        6501: ("б-г", "Берег"),
        6502: ("вал", "Вал"),
        6503: ("ж/р", "Жилой район"),
        6504: ("зона", "Зона (массив)"),
        6505: ("кв-л", "Квартал"),
        6506: ("мкр.", "Микрорайон"),
        6507: ("ост-в", "Остров"),
        6508: ("п/р", "Промышленный район"),
        6509: ("парк", "Парк"),
        6510: ("платф.", "Платформа"),
        6511: ("р-н", "Район"),
        6512: ("сад", "Сад"),
        6513: ("сквер", "Сквер"),
        6514: ("тер.", "Территория"),
        6515: ("тер. ГСК", "Территория ГСК"),
        6516: ("тер. ДНО", "Территория ДНО"),
        6517: ("тер. ДНП", "Территория ДНП"),
        6518: ("тер. ДНТ", "Территория ДНТ"),
        6519: ("тер. ДПК", "Территория ДПК"),
        6520: ("тер. ОНО", "Территория ОНО"),
        6521: ("тер. ОНП", "Территория ОНП"),
        6522: ("тер. ОНТ", "Территория ОНТ"),
        6523: ("тер. ОПК", "Территория ОПК"),
        6524: ("тер. СНО", "Территория СНО"),
        6525: ("тер. СНП", "Территория СНП"),
        6526: ("тер. СНТ", "Территория СНТ"),
        6527: ("тер. СПК", "Территория СПК"),
        6528: ("тер. ТСН", "Территория ТСН"),
        6529: ("тер.ф.х.", "Территория ФХ"),
        6530: ("ус.", "Усадьба"),
        6531: ("ю.", "Юрты"),
        6532: ("а/я", "Абонентский ящик"),
        6534: ("аал", "Аал"),
        6535: ("ал.", "Аллея"),
        6536: ("арбан", "Арбан"),
        6537: ("аул", "Аул"),
        6538: ("б-р", "Бульвар"),
        6539: ("взд.", "Въезд"),
        6540: ("г-к", "Городок"),
        6541: ("д.", "Деревня"),
        6542: ("дор.", "Дорога"),
        6543: ("ж/д б-ка", "Железнодорожная будка"),
        6544: ("ж/д к-ма", "Железнодорожная казарма"),
        6545: ("ж/д пл-ма", "Железнодорожная платформа"),
        6546: ("ж/д рзд.", "Железнодорожный разъезд"),
        6547: ("ж/д ст.", "Железнодорожная станция"),
        6548: ("ззд.", "Заезд"),
        6549: ("км", "Километр"),
        6550: ("коса", "Коса"),
        6551: ("к-цо", "Кольцо"),
        6552: ("лн.", "Линия"),
        6553: ("м-ко", "Местечко"),
        6554: ("наб.", "Набережная"),
        6555: ("п.", "посёлок"),
        6556: ("пер.", "Переулок"),
        6557: ("пер-д", "Переезд"),
        6558: ("п-к", "Починок"),
        6559: ("пл.", "Площадь"),
        6560: ("пл-ка", "Площадка"),
        6561: ("пр-д", "Проезд"),
        6562: ("пр-к", "Просек"),
        6563: ("пр-ка", "Просека"),
        6564: ("пр-кт", "Проспект"),
        6565: ("пр-лок", "Просёлок"),
        6566: ("проул.", "Проулок"),
        6567: ("рзд.", "Разъезд"),
        6568: ("с.", "Село"),
        6569: ("с-к", "Спуск"),
        6570: ("сл.", "Слобода"),
        6571: ("с-р", "Сквер"),
        6572: ("ст.", "Станция"),
        6573: ("стр.", "Строение"),
        6574: ("тракт", "Тракт"),
        6575: ("туп.", "Тупик"),
        6576: ("ул.", "Улица"),
        6577: ("х.", "Хутор"),
        6578: ("ш.", "Шоссе"),
        6579: ("гск", "Гаражно-строительный кооп."),
        6580: ("днп", "Дачное неком-е партнерство"),
        6581: ("местность", "Местность"),
        6582: ("мкр", "Микрорайон"),
        6583: ("н/п", "Некоммерческое партнерство"),
        6584: ("промзона", "Промышленная зона"),
        6585: ("снт", "Садовое товарищество"),
        6586: ("тер", "Территория"),
        6587: ("ф/х", "Фермерское хозяйство"),
        6588: ("месторожд.", "Месторождение"),
        6589: ("порт", "Порт"),
        6590: ("тер.СОСН", "Территория СОСН"),
        6591: ("тер. ТСЖ", "Территория ТСЖ"),
        6592: ("тер. ПК", "Территория ПК"),
        6594: ("мр.", "Месторождение"),
    },
    7: {
        701: ("аллея", "Аллея"),
        702: ("б-р", "Бульвар"),
        703: ("въезд", "Въезд"),
        704: ("дор", "Дорога"),
        705: ("жт", "Животноводческая точка"),
        706: ("заезд", "Заезд"),
        707: ("кв-л", "Квартал"),
        708: ("км", "Километр"),
        709: ("кольцо", "Кольцо"),
        710: ("линия", "Линия"),
        711: ("наб", "Набережная"),
        712: ("остров", "Остров"),
        713: ("парк", "Парк"),
        714: ("пер", "Переулок"),
        715: ("переезд", "Переезд"),
        716: ("пл", "Площадь"),
        717: ("пл-ка", "Площадка"),
        718: ("проезд", "Проезд"),
        719: ("пр-кт", "Проспект"),
        720: ("просек", "Просек"),
        721: ("Просёлок", "Просёлок"),
        722: ("проулок", "Проулок"),
        723: ("сад", "Сад"),
        724: ("сквер", "Сквер"),
        725: ("стр", "Строение"),
        726: ("тер", "Территория"),
        727: ("тракт", "Тракт"),
        728: ("туп", "Тупик"),
        729: ("ул", "Улица"),
        730: ("уч-к", "Участок"),
        731: ("ш", "Шоссе"),
        732: ("пр-д", "Проезд"),
        733: ("пр-к", "Просек"),
        734: ("пр-ка", "Просека"),
        735: ("г-к", "Городок"),
        736: ("д", "Деревня"),
        737: ("ж/д_будка", "Железнодорожная будка"),
        738: ("ж/д_казарм", "Железнодорожная казарма"),
        739: ("ж/д_оп", "ж/д останов. (обгонный) пункт"),
        740: ("ж/д_пост", "Железнодорожный пост"),
        741: ("ж/д_рзд", "Железнодорожный разъезд"),
        742: ("ж/д_ст", "Железнодорожная станция"),
        743: ("казарма", "Казарма"),
        744: ("м", "Местечко"),
        745: ("мкр", "Микрорайон"),
        746: ("нп", "Населённый пункт"),
        747: ("платф", "Платформа"),
        748: ("п", "посёлок"),
        749: ("п/о", "Почтовое отделение"),
        750: ("п/р", "Планировочный район"),
        751: ("п/ст", "посёлок и(при) станция(и)"),
        752: ("полустанок", "Полустанок"),
        753: ("пр-лок", "Просёлок"),
        754: ("рзд", "Разъезд"),
        755: ("с", "Село"),
        756: ("сл", "Слобода"),
        757: ("ст", "Станция"),
        758: ("х", "Хутор"),
        759: ("ж/д_платф", "Железнодорожная платформа"),
        760: ("проул.", "Проулок"),
        761: ("спуск", "Спуск"),
        762: ("ул.", "Улица"),
        763: ("гск", "Гаражно-строительный кооп."),
        764: ("снт", "Садовое неком-е товарищество"),
        765: ("ал.", "Аллея"),
        766: ("тер. ДНТ", "Территория ДНТ"),
        767: ("коса", "Коса"),
        768: ("вал", "Вал"),
        769: ("ферма", "Ферма"),
        770: ("мост", "Мост"),
        771: ("ряды", "Ряды"),
        772: ("а/я", "Абонентский ящик"),
        773: ("берег", "Берег"),
        774: ("просека", "Просека"),
        775: ("рзд.", "Разъезд"),
        776: ("бугор", "Бугор"),
        777: ("зона", "Зона"),
        778: ("ряд", "Ряд(ы)"),
        779: ("тер. СНТ", "Территория СНТ"),
        780: ("местность", "Местность"),
        781: ("балка", "Балка"),
        782: ("с/т", "Садовое товарищество"),
        783: ("пер-д", "Переезд"),
        784: ("сзд.", "Съезд"),
        785: ("маяк", "Маяк"),
        786: ("с-к", "Спуск"),
        787: ("днп", "Дачное неком-е партнерство"),
        788: ("н/п", "Некоммерческое партнерство"),
        789: ("ф/х", "Фермерское хозяйство"),
        790: ("промзона", "Промзона"),
        791: ("взв.", "Взвоз"),
        792: ("с-р", "Сквер"),
        793: ("ш.", "Шоссе"),
        794: ("ззд.", "Заезд"),
        795: ("к-цо", "Кольцо"),
        796: ("лн.", "Линия"),
        797: ("мгстр.", "Магистраль"),
        798: ("наб.", "Набережная"),
        799: ("пер.", "Переулок"),
    },
    75: {
        7501: ("з/у", "Земельный участок")
    },
    8: {
        801: ("ДОМ", "Дом"),
        802: ("влд.", "Владение"),
        803: ("д.", "Дом"),
        804: ("двлд.", "Домовладение"),
        805: ("зд.", "Здание"),
        806: ("к.", "Корпус"),
        807: ("кот.", "Котельная"),
        808: ("ОНС", "Объект незав. строительства"),
        809: ("пав.", "Павильон"),
        810: ("соор.", "Сооружение"),
        811: ("стр.", "Строение"),
        812: ("шахта", "Шахта"),
    },
    90: {
        9002: ("снт", "Садовое товарищество"),
        9003: ("промзона", "Промышленная зона"),
        9004: ("гск", "Гаражно-строительный кооп."),
        9005: ("тер", "Территория"),
        9006: ("мкр", "Микрорайон"),
        9007: ("сад", "Сад"),
        9008: ("ф/х", "Фермерское хозяйство"),
        9009: ("н/п", "Некоммерческое партнерство"),
        9010: ("днп", "Дачное неком-е партнерство"),
        9011: ("местность", "Местность"),
    },
    9: {
        901: ("г-ж", "Гараж"),
        902: ("кв.", "Квартира"),
        903: ("ком.", "Комната"),
        904: ("офис", "Офис"),
        905: ("п-б", "Погреб"),
        906: ("подв.", "Подвал"),
        907: ("помещ.", "Помещение"),
        908: ("раб.уч.", "Рабочий участок"),
        909: ("скл.", "Склад"),
        910: ("торг. зал", "Торговый зал"),
        911: ("цех", "Цех"),
        913: ("м/м", "Машино-место"),
    },
    91: {
        9101: ("аллея", "Аллея"),
        9102: ("б-р", "Бульвар"),
        9103: ("въезд", "Въезд"),
        9104: ("дор", "Дорога"),
        9105: ("жт", "Животноводческая точка"),
        9106: ("заезд", "Заезд"),
        9107: ("кв-л", "Квартал"),
        9108: ("км", "Километр"),
        9109: ("кольцо", "Кольцо"),
        9110: ("линия", "Линия"),
        9111: ("наб", "Набережная"),
        9112: ("остров", "Остров"),
        9113: ("парк", "Парк"),
        9114: ("пер", "Переулок"),
        9115: ("переезд", "Переезд"),
        9116: ("пл", "Площадь"),
        9117: ("пл-ка", "Площадка"),
        9118: ("проезд", "Проезд"),
        9119: ("пр-кт", "Проспект"),
        9120: ("просек", "Просек"),
        9121: ("Просёлок", "Просёлок"),
        9122: ("проулок", "Проулок"),
        9123: ("сад", "Сад"),
        9124: ("сквер", "Сквер"),
        9125: ("стр", "Строение"),
        9126: ("тер", "Территория"),
        9127: ("тракт", "Тракт"),
        9128: ("туп", "Тупик"),
        9129: ("ул", "Улица"),
        9130: ("уч-к", "Участок"),
        9131: ("ш", "Шоссе"),
        9132: ("аал", "Аал"),
        9133: ("аул", "Аул"),
        9134: ("высел", "Выселки(ок)"),
        9135: ("г-к", "Городок"),
        9136: ("д", "Деревня"),
        9137: ("ж/д_будка", "Железнодорожная будка"),
        9138: ("ж/д_казарм", "Железнодорожная казарма"),
        9139: ("ж/д_оп", "ж/д останов. (обгонный) пункт"),
        9140: ("ж/д_пост", "Железнодорожный пост"),
        9141: ("ж/д_рзд", "Железнодорожный разъезд"),
        9142: ("ж/д_ст", "Железнодорожная станция"),
        9143: ("казарма", "Казарма"),
        9144: ("м", "Местечко"),
        9145: ("мкр", "Микрорайон"),
        9146: ("нп", "Населённый пункт"),
        9147: ("платф", "Платформа"),
        9148: ("п", "посёлок"),
        9149: ("п/о", "Почтовое отделение"),
        9150: ("п/р", "Планировочный район"),
        9151: ("п/ст", "посёлок и(при) станция(и)"),
        9153: ("починок", "Починок"),
        9154: ("рзд", "Разъезд"),
        9155: ("с", "Село"),
        9156: ("сл", "Слобода"),
        9157: ("ст", "Станция"),
        9158: ("х", "Хутор"),
        9159: ("ж/д_платф", "Железнодорожная платформа"),
        9160: ("арбан", "Арбан"),
        9161: ("спуск", "Спуск"),
        9163: ("гск", "Гаражно-строит-ный кооператив"),
        9164: ("снт", "Садовое неком-е товарищество"),
        9167: ("коса", "Коса"),
        9168: ("вал", "Вал"),
        9169: ("ферма", "Ферма"),
        9170: ("мост", "Мост"),
        9171: ("ряды", "Ряды"),
        9172: ("а/я", "Абонентский ящик"),
        9173: ("берег", "Берег"),
        9174: ("просека", "Просека"),
        9177: ("зона", "Зона"),
    },
}


AddressFIASLevelType = int


@dataclass
class IAddressFIASType:
    addr_id: int = 0
    addr_short_name: str = ''
    addr_name: str = ''


class AddressFIASInfo:
    @staticmethod
    def get_levels() -> Generator[AddressFIASLevelType, Any, None]:
        return (level for level, _ in _address_fias_info.items())

    @staticmethod
    def get_address_types_by_level(level: int) -> Generator[IAddressFIASType, Any, None]:
        addrs = _address_fias_info.get(level)
        for addr_id, (short_name, name) in addrs:
            yield IAddressFIASType(
                addr_id=addr_id,
                addr_short_name=short_name,
                addr_name=name
            )

    @staticmethod
    def get_address_type_choices():
        return ((num, '%s' % name[0]) for lev, inf in _address_fias_info.items() for num, name in inf.items())
