from django.utils.translation import gettext_lazy as _


STUDY_PROGRAM_CHOICES = [
    ('medicine', _('Medicine and Surgery')),
    ('economics', _('Economics and Management')),
    ('law', _('Law')),
    ('psychology', _('Psychology')),
    ('education', _('Education Sciences')),
    ('nursing', _('Nursing')),
]

YEAR_OF_STUDY_CHOICES = [
    ('1', _('1st year')),
    ('2', _('2nd year')),
    ('3', _('3rd year')),
    ('4', _('4th year')),
    ('5', _('5th year')),
    ('6', _('6th year')),
    ('postgrad', _('Postgraduate')),
]

COUNTRY_CHOICES = [
    ('IT', _('Italy')),
    ('AL', _('Albania')),
    ('BR', _('Brazil')),
    ('CN', _('China')),
    ('FR', _('France')),
    ('DE', _('Germany')),
    ('IN', _('India')),
    ('NG', _('Nigeria')),
    ('ES', _('Spain')),
    ('TR', _('Turkey')),
    ('UA', _('Ukraine')),
    ('US', _('United States')),
    ('OTHER', _('Other')),
]

ALLOWED_EMAIL_DOMAINS = {'unicatt.it', 'icatt.it'}
