import logging

import requests

from azbankgateways.banks import BaseBank
from azbankgateways.exceptions import BankGatewayConnectionError, SettingDoesNotExist
from azbankgateways.exceptions.exceptions import BankGatewayRejectPayment
from azbankgateways.models import BankType, CurrencyEnum, PaymentStatus
from azbankgateways.utils import get_json, split_to_dict_querystring

class Sepehr(BaseBank):
    _terminal_code = None

    def __init__(self,**kwargs):
        super(Sepehr, self).__init__(**kwargs)
        self.set_gateway_currency(CurrencyEnum.IRR)
        self._token_api_url = "https://sandbox.banktest.ir/saderat/sepehr.shaparak.ir/V1/PeymentApi/GetToken"#"https://sepehr.shaparak.ir:8081/V1/PeymentApi/GetToken"
        self._payment_url ="https://sandbox.banktest.ir/saderat/sepehr.shaparak.ir/Pay" #"https://sepehr.shaparak.ir:8080/Pay"
        self._verify_api_url ="https://sandbox.banktest.ir/saderat/sepehr.shaparak.ir/V1/PeymentApi/Advice" #"https://sepehr.shaparak.ir:8081/V1/PeymentApi/Advice"


    def get_bank_type(self):
        return BankType.SEPEHR

    def set_default_settings(self):
        for item in ["TERMINAL_CODE"]:
            if item not in self.default_setting_kwargs:
                raise SettingDoesNotExist()
            setattr(self, f"_{item.lower()}", self.default_setting_kwargs[item])

    def get_minimum_amount(cls):
        return 10000
    """
    gateway
    """
    def _get_gateway_payment_url_parameter(self):
        return self._payment_url

    def _get_gateway_payment_parameter(self):
        params = {"token": self.get_reference_number(),"terminalID": self._terminal_code}
        return params

    def _get_gateway_payment_method_parameter(self):
        return "POST"

    """
    pay
    """
    def get_pay_data(self):

        data = {
            "Amount":self.get_gateway_amount(),
            "callbackURL": self._get_gateway_callback_url(),
            "invoiceID": self.get_tracking_code(),
            "terminalID": int(self._terminal_code),
            "Payload":{"oi":self.get_tracking_code(),"ou":self.get_mobile_number()},
        }
        return data

    def prepare_pay(self):
        super(Sepehr, self).prepare_pay()

    def pay(self):
        super(Sepehr, self).pay()
        data = self.get_pay_data()
        response_json = self._send_data(self._token_api_url, data)
        if response_json["Status"] == "0":
            token = response_json["AccessToken"]
            self._set_reference_number(token)
        else:
            logging.critical("Sepehr gateway reject payment")
            raise BankGatewayRejectPayment(self.get_transaction_status_text())
    """
    verify gateway
    """
    def prepare_verify_from_gateway(self):
        super(Sepehr, self).prepare_verify_from_gateway()
        for method in ["GET", "POST", "data"]:
            token = getattr(self.get_request(), method).get("digitalreceipt", None)
            tracking_code = getattr(self.get_request(), method).get("invoiceid", None)
            if tracking_code:
                self._set_tracking_code(tracking_code)
            if token:
                self._set_reference_number(token)
                self._set_bank_record()
                break

    def verify_from_gateway(self, request):
        super(Sepehr, self).verify_from_gateway(request)

    """
    verify
    """

    def get_verify_data(self):
        super(Sepehr, self).get_verify_data()
        data = {
            "digitalreceipt": self.get_reference_number(),
            "Tid": self._terminal_code,
        }
        return data

    def prepare_verify(self, tracking_code):
        super(Sepehr, self).prepare_verify(tracking_code)

    def verify(self, transaction_code):
        super(Sepehr, self).verify(transaction_code)
        data = self.get_verify_data()
        response_json = self._send_data(self._verify_api_url, data)
        if int(response_json["ReturnId"]) == self._gateway_amount :
            self._set_payment_status(PaymentStatus.COMPLETE)
            extra_information = json.dumps(response_json)
            self._bank.extra_information = extra_information
            self._bank.save()
        else:
            self._set_payment_status(PaymentStatus.CANCEL_BY_USER)
            logging.debug("Sepehr gateway unapprove payment")

    def _send_data(self, api, data):
        try:
            response = requests.post(api, json=data, timeout=10)

        except requests.Timeout:
            logging.exception("Sepehr time out gateway {}".format(data))
            raise BankGatewayConnectionError()
        except requests.ConnectionError:
            logging.exception("Sepehr time out gateway {}".format(data))
            raise BankGatewayConnectionError()
        response_json = get_json(response)
        if "respmsg" in response_json:
            message = response_json["respmsg"]
        elif "Message" in response_json:
            message = response_json["Message"]
        else:
            message = "No message found in response"
        self._set_transaction_status_text(message)
        return response_json