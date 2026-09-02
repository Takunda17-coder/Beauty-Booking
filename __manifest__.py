{
    'name': 'Beauty Booking',
    'version': '1.0.0',
    'category': 'Services',
    'summary': 'Booking platform for independent barbers and hairdressers',
    'description': """
        Beauty Booking
        ==============

        A booking platform for independent barbers
        and hairdressers.

        Features:
        - Professional profiles
        - Services
        - Availability
        - Customer bookings
        - Personal booking pages
    """,

    'author': 'Your Name',

    'depends': [
        'base',
        'web',
        'website',
        'mail',
    ],

    'data': [
        'data/sequence.xml',

        'security/security.xml',
        'security/ir.model.access.csv',
        'views/professional_views.xml',
        'views/availability_views.xml',
        'views/menus.xml',
        'views/booking_views.xml',
        'views/booking_search.xml',
        'views/booking_reports.xml',
        'views/service_views.xml',
        'web_views/booking_templates.xml',
        'web_views/portal_templates.xml'
    ],

    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}