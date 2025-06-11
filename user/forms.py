from django import forms
from .models import MissingPerson
import uuid

class MissingPersonForm(forms.ModelForm):
    class Meta:
        model = MissingPerson
        exclude = ['reporter', 'case_number', 'status', 'assigned_officer']
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

    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        if user:
            instance.reporter = user
            # Generate a unique case number
            instance.case_number = f"MP-{uuid.uuid4().hex[:8].upper()}"
        if commit:
            instance.save()
        return instance 