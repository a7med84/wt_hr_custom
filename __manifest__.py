{
    'name': 'Wide Techno HR Customizations',
    'version': '14.0.1',
    'summary': 'Wide Techno HR Customizations',
    'description': 'Wide Techno HR Customizations',
    'category': 'hr',
    'author': 'Hossam Galal',
    'depends': ['base', 'hr', 'wt_documents'],
    'data': [
        'security/ir.model.access.csv',
        'view/hr_job_offer.xml',
        'wizard/wizard_view.xml',
        'report/job_offer_report.xml',
    ],
    'installable': True,
    'auto_install': False
}
