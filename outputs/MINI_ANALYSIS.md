# Mini analysis: academic performance and recorded outcome

Question: How do first-semester grade and approved units differ by recorded outcome?

## Tidy sample

The first five cleaned rows are shown below with selected columns. The accompanying cleaned_sample.csv contains all cleaned columns for these rows. source_row is a snapshot reference, not a student identity.

| source_row | course_code | admission_grade | semester1_units_approved | semester1_grade | outcome |
| --- | --- | --- | --- | --- | --- |
| 1 | 171 | 127.3 | 0 | 0.0 | Dropout |
| 2 | 9254 | 142.5 | 6 | 14.0 | Graduate |
| 3 | 9070 | 124.8 | 0 | 0.0 | Dropout |
| 4 | 9773 | 119.6 | 6 | 13.42857143 | Graduate |
| 5 | 8014 | 141.5 | 5 | 12.33333333 | Graduate |

## Descriptive comparison

| Outcome | Students | Mean first-semester grade | Mean first-semester units approved |
| --- | ---: | ---: | ---: |
| Dropout | 1421 | 7.257 | 2.552 |
| Enrolled | 794 | 11.125 | 4.319 |
| Graduate | 2209 | 12.644 | 6.232 |

## Interpretation and cautions

In this collected snapshot, the Graduate group has higher mean first-semester grades and approved units than the Dropout group. This is a descriptive association, not evidence that an intervention raising grades will cause graduation.

These records come from one institutional setting. Outcome is measured at the end of the normal course duration; semester results are not available at admission. Using them as admission-time predictors would leak future information. Zero grades may have different explanations and should not be interpreted as lack of effort. The groups differ in size, and this comparison does not adjust for course or other differences.
