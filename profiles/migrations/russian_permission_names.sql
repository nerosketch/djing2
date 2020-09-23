PREPARE _tp (varchar(100), varchar(100), varchar(255)) AS
UPDATE auth_permission AS ap
SET name = $3 FROM django_content_type AS dct
WHERE dct.id = ap.content_type_id AND ap.codename = $2 AND dct.app_label = $1;


execute _tp('auth', 'change_permission', 'Может изменять права');
execute _tp('auth', 'delete_permission', 'Может удалять права');
execute _tp('auth', 'add_permission', 'Может добавлять права');
execute _tp('auth', 'view_permission', 'Может видеть права');
execute _tp('auth', 'change_group', 'Может изменять группы сотрудников');
execute _tp('auth', 'delete_group', 'Может удалять группы сотрудников');
execute _tp('auth', 'view_group', 'Может видеть группы сотрудников');
execute _tp('auth', 'add_group', 'Может добавлять группы сотрудников');
execute _tp('groupapp', 'change_group', 'Может изменять группы абонентов');
execute _tp('groupapp', 'view_group', 'Может видеть группы абонентов');
execute _tp('groupapp', 'add_group', 'Может добавлять группы абонентов');
execute _tp('groupapp', 'delete_group', 'Может удалять группы абонентов');
execute _tp('profiles', 'add_userprofile', 'Может добавлять учётки сотрудников');
execute _tp('profiles', 'change_userprofile', 'Может изменять учётки сотрудников');
execute _tp('profiles', 'delete_userprofile', 'Может удалять учётки сотрудников');
execute _tp('profiles', 'view_userprofile', 'Может видеть учётки сотрудников');
execute _tp('contenttypes', 'add_contenttype', 'Может добавлять типы объектов');
execute _tp('contenttypes', 'change_contenttype', 'Может изменять типы объектов');
execute _tp('contenttypes', 'view_contenttype', 'Может видеть типы объектов');
execute _tp('contenttypes', 'delete_contenttype', 'Может удалять типы объектов');
execute _tp('sessions', 'add_session', 'Может добавлять сессии');
execute _tp('sessions', 'change_session', 'Может изменять сессии');
execute _tp('sessions', 'view_session', 'Может видеть сессии');
execute _tp('sessions', 'delete_session', 'Может удалять сессии');
execute _tp('authtoken', 'add_token', 'Может добавлять токен авторизации');
execute _tp('authtoken', 'change_token', 'Может изменять токен авторизации');
execute _tp('authtoken', 'view_token', 'Может видеть токен авторизации');
execute _tp('authtoken', 'delete_token', 'Может удалять токен авторизации');
execute _tp('services', 'add_periodicpay', 'Может добавлять периодические платежи');
execute _tp('services', 'change_periodicpay', 'Может изменять периодические платежи');
execute _tp('services', 'view_periodicpay', 'Может видеть периодические платежи');
execute _tp('services', 'add_service', 'Может добавлять услуги');
execute _tp('services', 'change_service', 'Может изменять услуги');
execute _tp('services', 'view_service', 'Может видеть услуги');
execute _tp('services', 'change_oneshotpay', 'Может изменять единоразовые платежи');
execute _tp('services', 'delete_oneshotpay', 'Может удалять единоразовые платежи');
execute _tp('services', 'delete_periodicpay', 'Может удалять периодические платежи');
execute _tp('services', 'delete_service', 'Может удалять услуги');
execute _tp('services', 'add_oneshotpay', 'Может добавлять единоразовые платежи');
execute _tp('services', 'view_oneshotpay', 'Может видеть единоразовые платежи');
execute _tp('gateways', 'add_gateway', 'Может добавлять серверы доступа');
execute _tp('gateways', 'delete_gateway', 'Может удалять серверы доступа');
execute _tp('gateways', 'view_gateway', 'Может видеть серверы доступа');
execute _tp('gateways', 'change_gateway', 'Может изменять серверы доступа');
execute _tp('devices', 'add_device', 'Может добавлять устройства');
execute _tp('devices', 'change_device', 'Может изменять устройства');
execute _tp('devices', 'view_device', 'Может видеть устройства');
execute _tp('devices', 'add_port', 'Может добавлять порты устройств');
execute _tp('devices', 'delete_port', 'Может удалять порты устройств');
execute _tp('devices', 'view_port', 'Может видеть порты устройств');
execute _tp('devices', 'delete_device', 'Может удалять устройства');
execute _tp('devices', 'change_port', 'Может изменять порты устройств');
execute _tp('devices', 'can_toggle_ports', 'Может включать/выключать порты');
execute _tp('devices', 'can_remove_from_olt', 'Может удалять ONU с OLT');
execute _tp('devices', 'can_fix_onu', 'Может пользоваться кнопкой "Исправить"');
execute _tp('devices', 'can_apply_onu_config', 'Может применять конфиг для устройств с билинга');
execute _tp('customers', 'add_customer', 'Может добавлять абонентов');
execute _tp('customers', 'change_customer', 'Может изменять абонентов');
execute _tp('customers', 'view_customer', 'Может видеть абонентов');
execute _tp('customers', 'can_buy_service', 'Может покупать абоненту услугу');
execute _tp('customers', 'can_ping', 'Может пинговать абонентов');
execute _tp('customers', 'change_periodicpayforid', 'Может изменять периодический платёж');
execute _tp('customers', 'delete_periodicpayforid', 'Может удалять периодический платёж');
execute _tp('customers', 'add_passportinfo', 'Может добавлять паспортные данные');
execute _tp('customers', 'change_passportinfo', 'Может изменять паспортные данные');
execute _tp('customers', 'view_passportinfo', 'Может видеть паспортные данные');
execute _tp('customers', 'add_invoiceforpayment', 'Может добавлять долг для абонента');
execute _tp('customers', 'delete_invoiceforpayment', 'Может удалять долг для абонента');
execute _tp('customers', 'add_customerstreet', 'Может добавлять улицы');
execute _tp('customers', 'change_customerstreet', 'Может изменять улицы');
execute _tp('customers', 'delete_customerstreet', 'Может удалять улицы');
execute _tp('customers', 'view_customerstreet', 'Может видеть улицы');
execute _tp('customers', 'add_customerrawpassword', 'Может добавлять абонентский пароль');
execute _tp('customers', 'change_customerrawpassword', 'Может изменять абонентский пароль');
execute _tp('customers', 'add_customerservice', 'Может создавать абонентскую услугу');
execute _tp('customers', 'change_customerservice', 'Может изменять абонентскую услугу');
execute _tp('customers', 'delete_customerservice', 'Может удалять абонентскую услугу');
execute _tp('customers', 'view_customerservice', 'Может видеть абонентскую услугу');
execute _tp('customers', 'view_customerrawpassword', 'Может видеть абонентский пароль');
execute _tp('customers', 'change_additionaltelephone', 'Может изменять дополнительный номер телефона для абонента');
execute _tp('customers', 'view_additionaltelephone', 'Может видеть дополнительные номера телефонов для абонентов');
execute _tp('customers', 'delete_customer', 'Может удалять абонентов');
execute _tp('customers', 'can_add_balance', 'Может пополнять абоненту счёт');
execute _tp('customers', 'add_periodicpayforid', 'Может назначать периодический платёж');
execute _tp('customers', 'view_periodicpayforid', 'Может видеть периодический платёж');
execute _tp('customers', 'delete_passportinfo', 'Может удалять паспортные данные');
execute _tp('customers', 'change_invoiceforpayment', 'Может изменять долг для абонента');
execute _tp('customers', 'view_invoiceforpayment', 'Может видеть долг для абонента');
execute _tp('customers', 'can_complete_service', 'Может завершать услугу абонента');
execute _tp('customers', 'delete_customerrawpassword', 'Может удалять абонентский пароль');
execute _tp('customers', 'add_additionaltelephone', 'Может добавлять дополнительный номер телефона для абонента');
execute _tp('customers', 'delete_additionaltelephone', 'Может удалять дополнительный номер телефона для абонента');
execute _tp('customers', 'add_customerattachment', 'Может добавлять приложения к абонентам');
execute _tp('customers', 'change_customerattachment', 'Может изменять приложения к абонентам');
execute _tp('customers', 'delete_customerattachment', 'Может удалять приложения к абонентам');
execute _tp('customers', 'view_customerattachment', 'Может видеть приложения к абонентам');
execute _tp('customers', 'view_customerlog', 'Может видеть финансы абонентов');
execute _tp('messenger', 'add_messenger', 'Может добавлять мессенджеры');
execute _tp('messenger', 'delete_messenger', 'Может удалять мессенджеры');
execute _tp('messenger', 'view_messenger', 'Может видеть мессенджеры');
execute _tp('messenger', 'change_vibermessenger', 'Может изменять viber мессенджеры');
execute _tp('messenger', 'delete_vibermessenger', 'Может удалять viber мессенджеры');
execute _tp('messenger', 'view_vibermessenger', 'Может видеть viber мессенджеры');
execute _tp('messenger', 'change_messenger', 'Может изменять мессенджеры');
execute _tp('messenger', 'add_vibermessenger', 'Может добавлять viber мессенджеры');
execute _tp('tasks', 'change_task', 'Может изменять задачи');
execute _tp('tasks', 'delete_task', 'Может удалять задачи');
execute _tp('tasks', 'can_viewall', 'Имеет доступ ко всем задачам');
execute _tp('tasks', 'add_extracomment', 'Может комменировать задачи');
execute _tp('tasks', 'change_extracomment', 'Может изменять комментарии к задачам');
execute _tp('tasks', 'view_extracomment', 'Может видеть комментарии к задачам');
execute _tp('tasks', 'add_taskdocumentattachment', 'Может добавлять приложения к задачам');
execute _tp('tasks', 'change_taskdocumentattachment', 'Может изменять приложения к задачам');
execute _tp('tasks', 'delete_taskdocumentattachment', 'Может удалять приложения к задачам');
execute _tp('tasks', 'view_taskdocumentattachment', 'Может видеть приложения к задачам');
execute _tp('tasks', 'add_task', 'Может добавлять задачи');
execute _tp('tasks', 'view_task', 'Может видеть задачи');
execute _tp('tasks', 'can_remind', 'Может напоминать о задачах их исполнителям');
execute _tp('tasks', 'delete_extracomment', 'Может удалять комментарии к задачам');
execute _tp('fin_app', 'change_payalltimegateway', 'Может изменять платёжный шлюз AllTime');
execute _tp('fin_app', 'delete_payalltimegateway', 'Может удалять платёжный шлюз AllTime');
execute _tp('fin_app', 'view_payalltimegateway', 'Может видеть платёжный шлюз AllTime');
execute _tp('fin_app', 'add_payalltimegateway', 'Может добавлять платёжный шлюз AllTime');
execute _tp('msg_app', 'add_message', 'Может добавлять сообщения');
execute _tp('msg_app', 'change_message', 'Может изменять сообщения');
execute _tp('msg_app', 'delete_message', 'Может удалять сообщения');
execute _tp('msg_app', 'view_message', 'Может видеть сообщения');
execute _tp('msg_app', 'change_conversation', 'Может изменять беседу');
execute _tp('msg_app', 'delete_conversation', 'Может удалять беседу');
execute _tp('msg_app', 'view_conversation', 'Может видеть беседы');
execute _tp('msg_app', 'add_conversation', 'Может добавлять беседу');
execute _tp('networks', 'add_vlanif', 'Может добавлять vlan');
execute _tp('networks', 'change_vlanif', 'Может изменять vlan');
execute _tp('networks', 'delete_vlanif', 'Может удалять vlan');
execute _tp('networks', 'view_vlanif', 'Может видеть vlan');
execute _tp('networks', 'add_customeripleasemodel', 'Может добавлять ip адрес');
execute _tp('networks', 'change_customeripleasemodel', 'Может изменять ip адрес');
execute _tp('networks', 'delete_customeripleasemodel', 'Может удалять ip адрес');
execute _tp('networks', 'view_customeripleasemodel', 'Может видеть ip адрес');
execute _tp('networks', 'add_networkippool', 'Может добавлять подсеть');
execute _tp('networks', 'change_networkippool', 'Может изменять подсеть');
execute _tp('networks', 'delete_networkippool', 'Может удалять подсеть');
execute _tp('networks', 'view_networkippool', 'Может видеть подсети');
-- execute _tp('admin', 'add_logentry', 'Может добавлять логи');
-- execute _tp('admin', 'change_logentry', 'Может добавлять логи');
-- execute _tp('admin', 'delete_logentry', 'Может удалять логи');
-- execute _tp('admin', 'view_logentry', 'Может видеть логи');


deallocate _tp;
