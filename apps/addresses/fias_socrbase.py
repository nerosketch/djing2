from typing import Generator, Any, Optional
from dataclasses import dataclass

from djing2.lib import safe_int

_address_fias_info = {
    0: {
        'name': 'Не выбрано',
        'children': {
            0: ("-", "Не выбрано")
        }
    },
    1: {
        'name': 'Регион',
        'children': {
            1: ("стр", "Страна"),

            102: ('Аобл', 'Автономная область'),
            101: ('АО', 'Автономный округ'),
            103: ('г', 'Город'),
            112: ('г.ф.з.', 'Город федерального значения'),
            104: ('край', 'Край'),
            105: ('обл', 'Область'),
            107: ('округ', 'Округ'),
            106: ('Респ', 'Республика'),
            108: ('Чувашия', 'Чувашия'),
            # -------------------------------
            # 113: ("обл.", "Область"),
        }
    },
    2: {
        'name': 'Автономный округ',
        'children': {
            205: ('АО', 'Автономный округ'),
            207: ('вн.тер. г.', 'Внутригородская территория'),
            212: ('г', 'Город'),
            208: ('г.о.', 'Городской округ'),
            209: ('м.р-н', 'Муниципальный район'),
            206: ('п', 'Поселение'),
            201: ('р-н', 'Район'),
            203: ('тер', 'Территория'),
            202: ('у', 'Улус'),
        }
    },
    3: {
        'name': 'Район',
        'children': {
            310: ('волость', 'Волость'),
            301: ('г', 'Город'),
            305: ('дп', 'Дачный посёлок'),
            304: ('кп', 'Курортный посёлок'),
            316: ('массив', 'Массив'),
            317: ('п', 'Посёлок'),
            302: ('пгт', 'Посёлок городского типа'),
            311: ('п/о', 'Почтовое отделение'),
            303: ('рп', 'Рабочий посёлок'),
            320: ('с', 'Село'),
            307: ('с/а', 'Сельская администрация'),
            309: ('с/о', 'Сельский округ'),
            315: ('с/мо', 'Сельское муницип.образование'),
            314: ('с/п', 'Сельское поселение'),
            306: ('с/с', 'Сельсовет'),
            312: ('тер', 'Территория'),
            # -------------------------------
            # 301: ("р-н", "Район"),
        }
    },
    4: {
        'name': 'Город',
        'children': {
            401: ('аал', 'Аал'),
            445: ('автодорога', 'Автодорога'),
            440: ('арбан', 'Арбан'),
            402: ('аул', 'Аул'),
            403: ('волость', 'Волость'),
            404: ('высел', 'Выселки(ок)'),
            405: ('г', 'Город'),
            436: ('г-к', 'Городок'),
            449: ('гп', 'Городской посёлок'),
            407: ('дп', 'Дачный посёлок'),
            464: ('дп.', 'Дачный посёлок'),
            406: ('д', 'Деревня'),
            410: ('ж/д_оп', 'ж/д останов. (обгонный) пункт'),
            408: ('ж/д_будка', 'Железнодорожная будка'),
            457: ('ж/д в-ка', 'Железнодорожная ветка'),
            409: ('ж/д_казарм', 'Железнодорожная казарма'),
            338: ('ж/д_платф', 'Железнодорожная платформа'),
            452: ('ж/д пл-ка', 'Железнодорожная площадка'),
            413: ('ж/д_ст', 'Железнодорожная станция'),
            456: ('ж/д бл-ст', 'Железнодорожный блокпост'),
            459: ('ж/д к-т', 'Железнодорожный комбинат'),
            461: ('ж/д о.п.', 'Железнодорожный остановочный'),
            411: ('ж/д_пост', 'Железнодорожный пост'),
            460: ('ж/д п.п.', 'Железнодорожный путевой пост'),
            412: ('ж/д_рзд', 'Железнодорожный разъезд'),
            447: ('жилзона', 'Жилая зона'),
            446: ('жилрайон', 'Жилой район'),
            414: ('заимка', 'Заимка'),
            462: ('зим.', 'Зимовье'),
            415: ('казарма', 'Казарма'),
            439: ('кв-л', 'Квартал'),
            454: ('киш.', 'Кишлак'),
            444: ('кордон', 'Кордон'),
            416: ('кп', 'Курортный посёлок'),
            442: ('лпх', 'Леспромхоз'),
            448: ('массив', 'Массив'),
            417: ('м', 'Местечко'),
            418: ('мкр', 'Микрорайон'),
            419: ('нп', 'Населённый пункт'),
            463: ('нп.', 'Населённый пункт'),
            420: ('остров', 'Остров'),
            422: ('пл.р-н', 'Планировочный район'),
            443: ('погост', 'Погост'),
            421: ('п', 'Посёлок'),
            424: ('пгт', 'Посёлок городского типа'),
            423: ('п/ст', 'Посёлок и(при) станция(и)'),
            455: ('п. ж/д ст.', 'Посёлок при железнодорожной с'),
            468: ('п. ст.', 'Посёлок при станции (посёлок'),
            466: ('пос.рзд', 'Посёлок разъезда'),
            425: ('починок', 'Починок'),
            426: ('п/о', 'Почтовое отделение'),
            427: ('промзона', 'Промышленная зона'),
            429: ('рп', 'Рабочий посёлок'),
            428: ('рзд', 'Разъезд'),
            441: ('снт', 'Садовое неком-е товарищество'),
            430: ('с', 'Село'),
            467: ('сп', 'Сельский посёлок'),
            465: ('сп.', 'Сельский посёлок'),
            431: ('сл', 'Слобода'),
            433: ('ст-ца', 'Станица'),
            432: ('ст', 'Станция'),
            437: ('тер', 'Территория'),
            434: ('у', 'Улус'),
            435: ('х', 'Хутор'),
            # -------------------------------
            # 401: ("г", "Город"),
            # 402: ("пгт", "посёлок городского типа"),
            # 414: ("с/п", "Сельское поселение"),
            # 418: ("г.", "Город"),
        }
    },
    5: {
        'name': 'Внутригородская территория',
        'children': {
            934: ('аал', 'Аал'),
            572: ('а/я', 'Абонентский ящик'),
            501: ('аллея', 'Аллея'),
            936: ('арбан', 'Арбан'),
            937: ('аул', 'Аул'),
            581: ('балка', 'Балка'),
            901: ('берег', 'Берег'),
            576: ('бугор', 'Бугор'),
            502: ('б-р', 'Бульвар'),
            568: ('вал', 'Вал'),
            591: ('взв.', 'Взвоз'),
            503: ('въезд', 'Въезд'),
            563: ('гск', 'Гаражно-строительный кооп.'),
            535: ('городок', 'Городок'),
            587: ('днп', 'Дачное неком-е партнёрство'),
            536: ('д', 'Деревня'),
            504: ('дор', 'Дорога'),
            539: ('ж/д_оп', 'ж/д останов. (обгонный) пункт'),
            537: ('ж/д_будка', 'Железнодорожная будка'),
            538: ('ж/д_казарм', 'Железнодорожная казарма'),
            559: ('ж/д_платф', 'Железнодорожная платформа'),
            542: ('ж/д_ст', 'Железнодорожная станция'),
            540: ('ж/д_пост', 'Железнодорожный пост'),
            541: ('ж/д_рзд', 'Железнодорожный разъезд'),
            505: ('жт', 'Животноводческая точка'),
            903: ('ж/р', 'Жилой район'),
            506: ('заезд', 'Заезд'),
            577: ('зона', 'Зона'),
            543: ('казарма', 'Казарма'),
            507: ('кв-л', 'Квартал'),
            508: ('км', 'Километр'),
            509: ('кольцо', 'Кольцо'),
            567: ('коса', 'Коса'),
            510: ('линия', 'Линия'),
            597: ('мгстр.', 'Магистраль'),
            585: ('маяк', 'Маяк'),
            544: ('м', 'Местечко'),
            580: ('местность', 'Местность'),
            988: ('месторожд.', 'Месторождение'),
            545: ('мкр', 'Микрорайон'),
            570: ('мост', 'Мост'),
            511: ('наб', 'Набережная'),
            546: ('нп', 'Населённый пункт'),
            588: ('н/п', 'Некоммерческое партнёрство'),
            512: ('остров', 'Остров'),
            513: ('парк', 'Парк'),
            515: ('переезд', 'Переезд'),
            514: ('пер', 'Переулок'),
            550: ('пл.р-н', 'Планировочный район'),
            547: ('платф', 'Платформа'),
            517: ('пл-ка', 'Площадка'),
            516: ('пл', 'Площадь'),
            552: ('полустанок', 'Полустанок'),
            989: ('порт', 'Порт'),
            548: ('п', 'Посёлок'),
            551: ('п/ст', 'Посёлок и(при) станция(и)'),
            958: ('п-к', 'Починок'),
            549: ('п/о', 'Почтовое отделение'),
            518: ('проезд', 'Проезд'),
            590: ('промзона', 'Промзона'),
            520: ('просек', 'Просек'),
            574: ('просека', 'Просека'),
            521: ('просёлок', 'Просёлок'),
            519: ('пр-кт', 'Проспект'),
            522: ('проулок', 'Проулок'),
            554: ('рзд', 'Разъезд'),
            911: ('р-н', 'Район'),
            578: ('ряд', 'Ряд(ы)'),
            571: ('ряды', 'Ряды'),
            523: ('сад', 'Сад'),
            564: ('снт', 'Садовое неком-е товарищество'),
            -2: ('с/т', 'Садовое товарищество'),
            555: ('с', 'Село'),
            524: ('сквер', 'Сквер'),
            556: ('сл', 'Слобода'),
            561: ('спуск', 'Спуск'),
            557: ('ст', 'Станция'),
            525: ('стр', 'Строение'),
            584: ('сзд.', 'Съезд'),
            526: ('тер', 'Территория'),
            915: ('тер. ГСК', 'Территория ГСК'),
            916: ('тер. ДНО', 'Территория ДНО'),
            917: ('тер. ДНП', 'Территория ДНП'),
            566: ('тер. ДНТ', 'Территория ДНТ'),
            919: ('тер. ДПК', 'Территория ДПК'),
            920: ('тер. ОНО', 'Территория ОНО'),
            921: ('тер. ОНП', 'Территория ОНП'),
            922: ('тер. ОНТ', 'Территория ОНТ'),
            923: ('тер. ОПК', 'Территория ОПК'),
            992: ('тер. ПК', 'Территория ПК'),
            924: ('тер. СНО', 'Территория СНО'),
            925: ('тер. СНП', 'Территория СНП'),
            579: ('тер. СНТ', 'Территория СНТ'),
            990: ('тер.СОСН', 'Территория СОСН'),
            927: ('тер. СПК', 'Территория СПК'),
            991: ('тер. ТСЖ', 'Территория ТСЖ'),
            928: ('тер. ТСН', 'Территория ТСН'),
            929: ('тер.ф.х.', 'Территория ФХ'),
            527: ('тракт', 'Тракт'),
            528: ('туп', 'Тупик'),
            529: ('ул', 'Улица'),
            930: ('ус.', 'Усадьба'),
            530: ('уч-к', 'Участок'),
            569: ('ферма', 'Ферма'),
            589: ('ф/х', 'Фермерское хозяйство'),
            558: ('х', 'Хутор'),
            531: ('ш', 'Шоссе'),
            931: ('ю.', 'Юрты'),
        }
    },
    6: {
        'name': 'Дом',
        'children': {
            601: ('ДОМ', 'Дом'),
            # -------------------------------
            # 605: ("г", "Город"),
            # 607: ("дп", "Дачный посёлок"),
            # 621: ("п", "посёлок"),
            # 624: ("пгт", "посёлок городского типа"),
            # 629: ("рп", "Рабочий посёлок"),
            # 630: ("с", "Село"),
            # 651: ("пгт.", "посёлок городского типа"),
        }
    },
    # -------------------------------
    65: {
        'name': 'Планировочная структура',
        'children': {
            # 6506: ("мкр.", "Микрорайон"),
            # 6509: ("парк", "Парк"),
            # 6573: ("стр.", "Строение"),
            # 6576: ("ул.", "Улица"),
            # 6587: ("ф/х", "Фермерское хозяйство"),
        }
    },
    7: {
        'name': 'Улица',
        'children': {
            # 702: ("б-р", "Бульвар"),
            # 714: ("пер", "Переулок"),
            # 718: ("проезд", "Проезд"),
            # 719: ("пр-кт", "Проспект"),
            # 729: ("ул", "Улица"),
            # 762: ("ул.", "Улица"),
            # 793: ("ш.", "Шоссе"),
        }
    },
    8: {
        'name': 'Здание, сооружение, объект незавершенного строительства',
        'children': {
            # 803: ("д.", "Дом"),
            805: ("зд.", "Здание"),
            806: ("к.", "Корпус"),
            809: ("пав.", "Павильон"),
            811: ("стр.", "Строение"),
        }
    },
    90: {
        'name': 'Дополнительная территория',
        'children': {
            # 9002: ("снт", "Садовое товарищество"),
            # 9003: ("промзона", "Промышленная зона"),
            # 9004: ("гск", "Гаражно-строительный кооп."),
        }
    },
    9: {
        'name': 'Помещение в пределах здания, сооружения',
        'children': {
            901: ("г-ж", "Гараж"),
            902: ("кв.", "Квартира"),
            903: ("ком.", "Комната"),
            904: ("офис", "Офис"),
            905: ("п-б", "Погреб"),
            906: ("подв.", "Подвал"),
            907: ("помещ.", "Помещение"),
            909: ("скл.", "Склад"),
        }
    },
    91: {
        'name': 'Объект, подчиненный дополнительной территории',
        'children': {
            9125: ("стр", "Строение"),
            9130: ("уч-к", "Участок"),
        }
    },
}

AddressFIASLevelType = int


@dataclass(frozen=True)
class IAddressFIASType:
    addr_code: int = 0
    addr_short_name: str = ''
    addr_name: str = ''


class AddressFIASInfo:
    @staticmethod
    def get_levels() -> Generator[tuple[AddressFIASLevelType, str], Any, None]:
        for level, obj in _address_fias_info.items():
            name = obj.get('name')
            if name:
                yield level, name

    @staticmethod
    def get_address_types_by_level(level: AddressFIASLevelType) -> Generator[IAddressFIASType, Any, None]:
        level = safe_int(level, default=None)
        addr = _address_fias_info.get(level)
        if not addr:
            raise ValueError('Unknown level passed: %d' % level)
        for addr_code, (short_name, name) in addr.get('children').items():
            yield IAddressFIASType(
                addr_code=addr_code,
                addr_short_name=short_name,
                addr_name=name
            )

    @staticmethod
    def get_address(addr_code: int) -> Optional[IAddressFIASType]:
        levels = (level for level, _ in AddressFIASInfo.get_levels())
        r = (a for level in levels for a in AddressFIASInfo.get_address_types_by_level(level=level) if a.addr_code == addr_code)
        return next(r, None)

    @staticmethod
    def get_address_types_map() -> dict[int, IAddressFIASType]:
        levels = (level for level, _ in AddressFIASInfo.get_levels())
        return {
            a.addr_code: a for level in levels for a in AddressFIASInfo.get_address_types_by_level(level=level)
        }

    @staticmethod
    def get_address_type_choices():
        for _, inf in _address_fias_info.items():
            children = inf.get('children')
            for child_num, (child_short_name, child_long_name) in children.items():
                # yield child_num, "%s (%s)" % (child_short_name, child_long_name)
                yield child_num, child_short_name

    @staticmethod
    def get_level_name(level: AddressFIASLevelType) -> Optional[str]:
        lev = _address_fias_info.get(level, None)
        if lev is not None:
            return lev.get('name', None)
