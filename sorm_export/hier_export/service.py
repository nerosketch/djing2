from .base import exp_dec, format_fname


@exp_dec
def export_nomenclature():
    """
    Файл выгрузки номенклатуры, версия 1.
    В этом файле выгружаются все услуги, предоставляемые оператором своим абонентам - номенклатура-справочник.
    """
    fname = f'service_list_v1_{format_fname()}.txt'
    dat = [{
        ''
    }]
