from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from hijri_converter import convert
from io import BytesIO
import base64
import qrcode
from num2words import num2words
import re
import itertools

arabic_chars = ""
for s in itertools.chain(range(1569, 1595), range(1600, 1620), range(65269, 65276, 2)):
    arabic_chars += chr(s)


def generate_qr_code(url):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=20,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image()
    temp = BytesIO()
    img.save(temp, format="PNG")
    qr_img = base64.b64encode(temp.getvalue())
    return qr_img


def convert_to_hijri(value):
    return convert.Gregorian(value.year, value.month, value.day).to_hijri()


class JobOffer(models.Model):
    _name = 'wide.job.offer'
    _description = 'Job Offer Record'

    @api.onchange('ar_name')
    def onchange_ar_name(self):
        if self.ar_name:
            if re.search(f"[^{arabic_chars}\s]", self.ar_name, ) != None:
                raise ValidationError("يجب ألا يحتوى الاسم باللغه العربية أحرف غير عربية")
            self.subject = 'عرض عمل ' + self.ar_name

    @api.onchange('en_name')
    def onchange_en_name(self):
        if self.en_name:
            if re.search("[^a-zA-Z\s]", self.en_name, ) != None:
                raise ValidationError("يجب ألا يحتوى الاسم باللغه الانجليزية أحرف غير انجليزية")

    @api.onchange('job_ar_name')
    def onchange_job_ar_name(self):
        if self.job_ar_name:
            if re.search(f"[^{arabic_chars}\s]", self.job_ar_name, ) != None:
                raise ValidationError("يجب ألا يحتوى مسمى الوظيفة باللغه العربية أحرف غير عربية")

    @api.onchange('job_en_name')
    def onchange_job_en_name(self):
        if self.job_en_name:
            if re.search("[^a-zA-Z\s]", self.job_en_name, ) != None:
                raise ValidationError("يجب ألا يحتوى مسمى الوظيفة باللغه الانجليزية أحرف غير انجليزية")

    def get_hr_department(self):
        department = self.env['wide.department'].search([('hr_department', '=', True)], limit=1)
        return department

    seq = fields.Char(string='Seq', default="New", copy=False)
    name = fields.Char(string='رقم المعاملة', compute="compute_name", copy=False)
    department_id = fields.Many2one(comodel_name='wide.department', string='الإدارة', default=get_hr_department)
    subject = fields.Char(string='الموضوع', default='عرض عمل')
    ar_name = fields.Char(string='الاسم باللغه العربية')
    en_name = fields.Char(string='الاسم باللغه الانجليزية')
    job_ar_name = fields.Char(string='مسمى الوظيفة باللغه العربية')
    job_en_name = fields.Char(string='مسمى الوظيفة باللغه الانجليزية')
    offer_period = fields.Integer(string='مدة العرض')
    contract_type = fields.Selection(string='نوع العقد', selection=[('Full', 'دوام كامل'), ('Part', 'دوام جزئي'), ],
                                     default='Full')
    day_hours = fields.Float(string='عدد ساعات العمل يوميًّا')
    week_hours = fields.Float(string='عدد ساعات العمل أسبوعيًّا')
    total_salary = fields.Float(string='الراتب الإجمالي')
    qr_code = fields.Char(string='Qr Code', copy=False)

    #

    document_config_id = fields.Many2one(comodel_name='document.config', string='إعداد الخطاب')
    date = fields.Date(string='التاريخ', default=lambda self: fields.date.today())
    date_hijri = fields.Char(string="التاريخ الهجري", compute="_onchange_dates")

    email_message = fields.Text(string="رسالة الإيميل", )
    received_ids = fields.Many2many(comodel_name='res.partner', string='المستلمون', copy=False)
    confirm_date = fields.Datetime(string='تاريخ الإعتماد')
    confirm_user_id = fields.Many2one(comodel_name='res.users', string='اعتمد بواسطة')
    state = fields.Selection(
        string='الحاله',
        selection=[('draft', 'مسوده'),
                   ('confirm', 'مؤكد'), ],
        default="draft", )

    editable_user_ids = fields.Many2many('res.users', 'res_users_wide_job_offer', 'custom10', 'custom_rel10',
                                         string='المستخدمين المسؤلون عن التعديل')
    confirm_user_ids = fields.Many2many('res.users', 'res_users_wide_job_offer1', 'custom20', 'custom_rel20',
                                        string='المستخدمين المسؤلون عن التأكيد')
    
    attachments = fields.Many2many(comodel_name='ir.attachment', string='المرفقات')
    attachments_str = fields.Char('File Name')

    @api.onchange('attachment')
    def onchange_attachment(self):
        for rec in self:
            names = []
            for line in rec.attachment:
                names += str(line.name)
            rec.attachments_str = ''.join(names)

    @api.depends("seq", "department_id.code")
    def compute_name(self):
        for rec in self:
            today = fields.Date.today()
            hijri_year = str(convert_to_hijri(today))[2:4:1]
            rec.name = str(hijri_year) + str(rec.department_id.code) + str(rec.seq)

    @api.model
    def create(self, values):
        values['seq'] = self.env['ir.sequence'].next_by_code('wide.documents.seq') or 'New'
        result = super(JobOffer, self).create(values)
        return result

    def _get_api_code(self, report_info):
        if len(report_info.split(".")) == 2:
            attach_model = report_info.split(".")[0]
            attach_type = report_info.split(".")[1]
        else:
            return False

        url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        query = "/qr/attachment/download/"
        attach_id = self.env['ir.attachment'].sudo().search([('res_id', '=', self.id),
                                                             ('attach_model', '=', attach_model),
                                                             ('attach_type', '=', attach_type)]).id
        if not attach_id:
            return False
        url += query + str(attach_id)
        self.qr_code = url
        return url

    #
    @api.depends("date")
    def _onchange_dates(self):
        today = fields.Date.today()
        if self.date:
            if self.date.year < 1925 or self.date > today:
                raise ValidationError("لا يمكن ادخال تاريخ قبل 1925 وبعد تاريخ اليوم")
        # Just define 12 months names:
        islamic_months = ["محرم", "صفر", "ربيع اﻷول",
                          "ربيع الثاني", "جمادى الأول",
                          "جمادى الثاني", "رجب", "شعبان",
                          "رمضان", "شوال", "ذوالقعدة", "ذو الحجة"]
        # On the next step get the right name:
        # hijri_date[2] = islamic_months[hijri_month - 1]  # 1 <= hijri_month <= 12
        for rec in self:
            if rec.date:
                # print(convert_to_hijri(rec.date))
                hijri_month = str(convert_to_hijri(rec.date))[5:7:1]
                # print(hijri_month)
                date_higri = str(convert_to_hijri(rec.date))[:5:1] + islamic_months[int(hijri_month) - 1] + str(
                    convert_to_hijri(rec.date))[7::1]
                # print(date_higri)
                rec.date_hijri = str(date_higri)

    def action_send_document(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('إرسال العرض'),
            'view_mode': 'form',
            'res_model': 'send.job.offer',
            'target': 'new',
            'context': {
                'default_job_offer_id': self.id,
            },
        }

    def confirm_document(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('تأكيد العرض'),
            'view_mode': 'form',
            'res_model': 'confirm.job.offer',
            'target': 'new',
            'context': {
                'default_job_offer_id': self.id,
            },
        }
