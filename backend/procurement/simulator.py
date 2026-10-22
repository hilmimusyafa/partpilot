"""Deterministic synthetic replies. No network, phone number, or WhatsApp session."""
from datetime import datetime, timedelta
from decimal import Decimal
from .models import VendorResponse, Quote

VENDORS={
 'SIM-ENOUGH':{'quantity':'100','price':'150000','shipping':'20000','hours':6},
 'SIM-SHORT':{'quantity':'2','price':'130000','shipping':'20000','hours':4},
 'SIM-REFUSE':{'quantity':'100','price':'190000','shipping':'30000','hours':8},
 'SIM-REVISE':{'quantity':'100','price':'180000','shipping':'25000','hours':5},
 'SIM-SILENT':{'quantity':None,'price':None,'shipping':None,'hours':None},
}

class DemoSimulator:
    def send(self,event):
        vendor=event['vendor_id'];p=event['payload'];data=VENDORS[vendor]
        envelope={'event_id':event['id'],'run_id':event['run_id'],'vendor_id':vendor}
        if vendor=='SIM-SILENT':
            # This is a simulated deadline outcome, not an assertion of zero stock.
            return VendorResponse(**envelope,outcome='no_response')
        counter=event['kind']=='price_counteroffer'
        if counter and vendor=='SIM-REFUSE':
            return VendorResponse(**envelope,outcome='negotiation_refused')
        requested=datetime.fromisoformat(p['requested_at'])
        price=data['price']
        if counter: price=str(min(Decimal(price),Decimal(p['target_unit_price'])))
        quote=Quote(quote_id=f"{event['run_id']}:{vendor}",revision=2 if counter else 1,
                    identity=p['identity'],qty_available=data['quantity'],unit_price=price,
                    tax_amount='0',shipping_amount=data['shipping'],processing_hours='1',
                    delivered_eta=requested+timedelta(hours=data['hours']),
                    destination_warehouse_id=p['destination_warehouse_id'],
                    valid_until=datetime.fromisoformat(p['expires_at']))
        return VendorResponse(**envelope,outcome='revised_quote' if counter else 'quoted',quote=quote)
