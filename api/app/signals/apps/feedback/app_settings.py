# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2019 - 2021 Gemeente Amsterdam
"""
Django app settings defaults for feedback app.

Note: do not edit this file for a specific deployment. Override in the project's
central settings files instead. This file serves to provide reasonable defaults
and documents what they do.
"""
# Note: prepend all settings in this file with FEEDBACK_

# Number of days after closing of an issue that feedback is still accepted.
FEEDBACK_EXPECTED_WITHIN_N_DAYS = 14

# The feedback application generates links to the SIA frontend application.
# Where that application is running (its URL) cannot always be determined from
# the requests, for instance, for code running in Celery tasks. Hence the
# use of a `ENVIRONMENT` environment variable to figure out where the SIA
# backend is running.
FEEDBACK_ENV_FE_MAPPING = {
    'LOCAL': 'http://dummy_link',
}
