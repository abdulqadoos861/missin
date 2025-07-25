from django import forms
from .models import MissingPerson
import uuid
from datetime import datetime

class MissingPersonForm(forms.ModelForm):
    class Meta:
        model = MissingPerson
        exclude = ['reporter', 'case_number', 'status', 'assigned_officer', 'location_found', 'found_date']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'last_seen_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'distinguishing_marks': forms.Textarea(attrs={'rows': 3}),
            'last_seen_wearing': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            # For file inputs, use a custom class to hide them, as they have custom styling.
            if isinstance(field.widget, forms.ClearableFileInput):
                field.widget.attrs['class'] = 'custom-file-input'
            else:
                field.widget.attrs['class'] = 'form-control'
            
            # Mark required fields
            if field.required:
                field.widget.attrs['required'] = 'required'

    def clean(self):
        cleaned_data = super().clean()
        
        # Validate date of birth is not in future
        dob = cleaned_data.get('date_of_birth')
        if dob and dob > datetime.now().date():
            self.add_error('date_of_birth', 'Date of birth cannot be in the future')

        # Validate last seen date
        last_seen = cleaned_data.get('last_seen_date')
        if last_seen and last_seen > datetime.now().date():
            self.add_error('last_seen_date', 'Last seen date cannot be in the future')

        # Validate age matches date of birth
        age = cleaned_data.get('age')
        if dob and age:
            calculated_age = (datetime.now().date() - dob).days // 365
            if abs(calculated_age - age) > 1:  # Allow 1 year difference due to months
                self.add_error('age', 'Age does not match the date of birth')

        return cleaned_data

    def generate_case_number(self):
        """Generate a unique case number with format: MP-YYYYMMDD-XXXX"""
        date_str = datetime.now().strftime('%Y%m%d')
        while True:
            random_str = uuid.uuid4().hex[:4].upper()
            case_number = f"MP-{date_str}-{random_str}"
            # Check if this case number already exists
            if not MissingPerson.objects.filter(case_number=case_number).exists():
                return case_number

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        
        if not instance.pk:  # Only for new instances
            if user:
                instance.reporter = user
            # Generate and set case number
            instance.case_number = self.generate_case_number()
            instance.status = 'pending'  # Set initial status
        
        if commit:
            instance.save()
            # Save many-to-many fields if any
            self.save_m2m()
        
        return instance 