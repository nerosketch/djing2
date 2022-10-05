# Generated by Django 3.1.14 on 2022-09-30 13:46

from django.db import migrations, models


def _update_addr_types(apps, schema_editor):
    address_model = apps.get_model('addresses', 'AddressModel')
    update_info = (
        # old_ao_type, new_ao_type, new_ao_level
        (113,  105, 1),     # Область
        (301,  201, 2),     # Район
        (401,  405, 4),     # Город
        (402,  424, 4),     # Посёлок городского типа
        (414,  314, 3),     # Сельское поселение
        (3503, 314, 3),     # Сельское поселение
        (418,  405, 4),     # Город
        (605,  405, 4),     # Город
        (607,  407, 4),     # Дачный посёлок
        (621,  421, 4),     # Посёлок
        (624,  424, 4),     # Посёлок городского типа
        (629,  429, 4),     # Рабочий посёлок
        (630,  430, 4),     # Село
        (651,  424, 4),     # Посёлок городского типа
        (6506, 418, 4),     # Микрорайон
        (6509, 513, 5),     # Парк
        (6573, 525, 5),     # Строение
        (6576, 529, 5),     # Улица
        (6587, 589, 5),     # Фермерское хозяйство
        (702,  502, 5),     # Бульвар
        (714,  514, 5),     # Переулок
        (718,  518, 5),     # Проезд
        (719,  519, 5),     # Проспект
        (729,  529, 5),     # Улица
        (762,  529, 5),     # Улица
        (793,  531, 5),     # Шоссе
        (803,  601, 6),     # Дом
        (805,  805, 6),     # Здание
        (806,  806, 6),     # Корпус
        (809,  809, 6),     # Павильон
        (811,  525, 5),     # Строение
        (9002, 564, 5),     # Садовое неком-е товарищество
        (9003, 590, 5),     # Промзона
        (9004, 563, 5),     # Гаражно-строительный кооп.
        (901,  610, 6),     # Гараж
        (902,  902, 6),     # Квартира
        (903,  620, 6),     # Комната
        (904,  904, 6),     # Офис
        (905,  905, 6),     # Погреб
        (906,  906, 6),     # Подвал
        (907,  907, 6),     # Помещение
        (909,  909, 6),     # Склад
        (9125, 525, 5),     # Строение
        (9130, 530, 5),     # Участок
    )
    for old_ao_type, new_ao_type, new_ao_level in update_info:
        r = address_model.objects.filter(fias_address_type=old_ao_type).update(
            fias_address_level=new_ao_level,
            fias_address_type=new_ao_type,
        )
        print(f'Updated ao {old_ao_type} -> {new_ao_type} L{new_ao_level}', r)


class Migration(migrations.Migration):

    dependencies = [
        ('addresses', '0003_remove_addr_types'),
    ]

    operations = [
        migrations.AlterField(
            model_name='addressmodel',
            name='fias_address_level',
            field=models.IntegerField(blank=True, choices=[(0, 'Не выбрано'), (1, 'Регион'), (2, 'Автономный округ'),
                                                           (3, 'Район'), (4, 'Город'),
                                                           (5, 'Внутригородская территория'), (6, 'Дом')],
                                      default=None, null=True, verbose_name='Address Level'),
        ),
        migrations.AlterField(
            model_name='addressmodel',
            name='fias_address_type',
            field=models.IntegerField(
                choices=[(0, '-'), (1, 'стр'), (102, 'Аобл'), (101, 'АО'), (103, 'г'), (112, 'г.ф.з.'), (104, 'край'),
                         (105, 'обл'), (107, 'округ'), (106, 'Респ'), (108, 'Чувашия'), (205, 'АО'),
                         (207, 'вн.тер. г.'), (212, 'г'), (208, 'г.о.'), (209, 'м.р-н'), (206, 'п'), (201, 'р-н'),
                         (203, 'тер'), (202, 'у'), (310, 'волость'), (301, 'г'), (305, 'дп'), (304, 'кп'),
                         (316, 'массив'), (317, 'п'), (302, 'пгт'), (311, 'п/о'), (303, 'рп'), (320, 'с'),
                         (307, 'с/а'), (309, 'с/о'), (315, 'с/мо'), (314, 'с/п'), (306, 'с/с'), (312, 'тер'),
                         (401, 'аал'), (445, 'автодорога'), (440, 'арбан'), (402, 'аул'), (403, 'волость'),
                         (404, 'высел'), (405, 'г'), (436, 'г-к'), (449, 'гп'), (407, 'дп'), (464, 'дп.'), (406, 'д'),
                         (410, 'ж/д_оп'), (408, 'ж/д_будка'), (457, 'ж/д в-ка'), (409, 'ж/д_казарм'),
                         (338, 'ж/д_платф'), (452, 'ж/д пл-ка'), (413, 'ж/д_ст'), (456, 'ж/д бл-ст'),
                         (459, 'ж/д к-т'), (461, 'ж/д о.п.'), (411, 'ж/д_пост'), (460, 'ж/д п.п.'), (412, 'ж/д_рзд'),
                         (447, 'жилзона'), (446, 'жилрайон'), (414, 'заимка'), (462, 'зим.'), (415, 'казарма'),
                         (439, 'кв-л'), (454, 'киш.'), (444, 'кордон'), (416, 'кп'), (442, 'лпх'), (448, 'массив'),
                         (417, 'м'), (418, 'мкр'), (419, 'нп'), (463, 'нп.'), (420, 'остров'), (422, 'пл.р-н'),
                         (443, 'погост'), (421, 'п'), (424, 'пгт'), (423, 'п/ст'), (455, 'п. ж/д ст.'),
                         (468, 'п. ст.'), (466, 'пос.рзд'), (425, 'починок'), (426, 'п/о'), (427, 'промзона'),
                         (429, 'рп'), (428, 'рзд'), (441, 'снт'), (430, 'с'), (467, 'сп'), (465, 'сп.'), (431, 'сл'),
                         (433, 'ст-ца'), (432, 'ст'), (437, 'тер'), (434, 'у'), (435, 'х'), (934, 'аал'),
                         (572, 'а/я'), (501, 'аллея'), (936, 'арбан'), (937, 'аул'), (581, 'балка'), (901, 'берег'),
                         (576, 'бугор'), (502, 'б-р'), (568, 'вал'), (591, 'взв.'), (503, 'въезд'), (563, 'гск'),
                         (535, 'городок'), (587, 'днп'), (536, 'д'), (504, 'дор'), (539, 'ж/д_оп'),
                         (537, 'ж/д_будка'), (538, 'ж/д_казарм'), (559, 'ж/д_платф'), (542, 'ж/д_ст'),
                         (540, 'ж/д_пост'), (541, 'ж/д_рзд'), (505, 'жт'), (903, 'ж/р'), (506, 'заезд'),
                         (577, 'зона'), (543, 'казарма'), (507, 'кв-л'), (508, 'км'), (509, 'кольцо'), (567, 'коса'),
                         (510, 'линия'), (597, 'мгстр.'), (585, 'маяк'), (544, 'м'), (580, 'местность'),
                         (988, 'месторожд.'), (545, 'мкр'), (570, 'мост'), (511, 'наб'), (546, 'нп'), (588, 'н/п'),
                         (512, 'остров'), (513, 'парк'), (515, 'переезд'), (514, 'пер'), (550, 'пл.р-н'),
                         (547, 'платф'), (517, 'пл-ка'), (516, 'пл'), (552, 'полустанок'), (989, 'порт'), (548, 'п'),
                         (551, 'п/ст'), (958, 'п-к'), (549, 'п/о'), (518, 'проезд'), (590, 'промзона'),
                         (520, 'просек'), (574, 'просека'), (521, 'просёлок'), (519, 'пр-кт'), (522, 'проулок'),
                         (554, 'рзд'), (911, 'р-н'), (578, 'ряд'), (571, 'ряды'), (523, 'сад'), (564, 'снт'),
                         (-2, 'с/т'), (555, 'с'), (524, 'сквер'), (556, 'сл'), (561, 'спуск'), (557, 'ст'),
                         (525, 'стр'), (584, 'сзд.'), (526, 'тер'), (915, 'тер. ГСК'), (916, 'тер. ДНО'),
                         (917, 'тер. ДНП'), (566, 'тер. ДНТ'), (919, 'тер. ДПК'), (920, 'тер. ОНО'),
                         (921, 'тер. ОНП'), (922, 'тер. ОНТ'), (923, 'тер. ОПК'), (992, 'тер. ПК'), (924, 'тер. СНО'),
                         (925, 'тер. СНП'), (579, 'тер. СНТ'), (990, 'тер.СОСН'), (927, 'тер. СПК'),
                         (991, 'тер. ТСЖ'), (928, 'тер. ТСН'), (929, 'тер.ф.х.'), (527, 'тракт'), (528, 'туп'),
                         (529, 'ул'), (930, 'ус.'), (530, 'уч-к'), (569, 'ферма'), (589, 'ф/х'), (558, 'х'),
                         (531, 'ш'), (931, 'ю.'), (601, 'ДОМ'), (805, 'зд.'), (806, 'к.'), (809, 'пав.'),
                         (902, 'кв.'), (904, 'офис'), (905, 'п-б'), (906, 'подв.'), (907, 'помещ.'), (909, 'скл.'),
                         (610, 'г-ж'), (620, 'ком.')], default=0, verbose_name='FIAS address type'),
        ),
        migrations.RunPython(_update_addr_types)
    ]
