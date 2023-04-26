from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import base64
import re


class ConfirmJobOffer(models.TransientModel):
    _name = 'confirm.job.offer'
    _description = 'Confirm Job Offer'

    job_offer_id = fields.Many2one(comodel_name='wide.job.offer', string='الخطاب')

    def confirm_document(self):
        if self.job_offer_id:
            self.job_offer_id.state = 'confirm'
            self.job_offer_id.confirm_date = fields.Datetime.now()
            self.job_offer_id.confirm_user_id = self.env.user


class SendJobOffer(models.TransientModel):
    _name = 'send.job.offer'
    _description = 'Send Job Offer'

    job_offer_id = fields.Many2one(comodel_name='wide.job.offer', string='الخطاب')
    private_email1 = fields.Char('البريد الإلكتروني')

    @api.onchange('private_email1')
    def check_private_email1(self):
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        # pass the regular expression
        # and the string into the fullmatch() method
        if self.private_email1:
            if re.fullmatch(regex, self.private_email1):
                pass
            else:
                raise ValidationError("Invalid Email")

    def send_email_with_attachment(self):
        if self.job_offer_id:
            report_template_id = self.env.ref('wt_hr_custom.job_offer_report').sudo()._render_qweb_pdf(
                self.job_offer_id.id)
            data_record = base64.b64encode(report_template_id[0])
            ir_values = {
                'name': "عرض العمل" + '.pdf',
                'type': 'binary',
                'datas': data_record,
                'store_fname': data_record,
                'mimetype': 'application/x-pdf',
            }
            data_id = self.env['ir.attachment'].create(ir_values)

            # lines = [(6, 0, [self.document_id.files.ids]), (4, data_id.id)]
            # print("lineslineslines", lines)
            attachments = []
            attachments.append(data_id.id)
            values = {
                'subject': self.job_offer_id.document_config_id.company_id.partner_id.name,
                'author_id': self.env.company.partner_id.id,
                'email_to': self.private_email1,
                'email_from': 'no-reply@wtsaudi.com',
                'state': 'outgoing',
                'body_html': self.job_offer_id.email_message,
                # 'recipient_ids': self.partner_id,
                'attachment_ids': [(6, 0, [x for x in attachments])],
            }
            template = self.env['mail.mail'].create(values)
            template.send()
            # self.job_offer_id.received_ids = [(4, paetner.id)]
        return True
