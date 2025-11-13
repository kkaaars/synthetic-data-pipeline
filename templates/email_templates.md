# Email templates

## Formal Invoice Email
From: {from_email}
To: {to_email}
Subject: Invoice {invoice_id} - Payment details

Dear {recipient},

Please find below the payment details for invoice {invoice_id}.

{sits_block}

Amount due: {amount} USD
Due date: {due_date}

If you need anything else, please let me know.

Best regards,
{sender}
---

## Short Notification
From: {from_email}
To: {to_email}
Subject: Payment confirmation

Hi {recipient},

We have processed the payment. Reference: {reference}.

{sits_block}

Thanks,
{sender}
