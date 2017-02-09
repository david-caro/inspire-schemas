# -*- coding: utf-8 -*-
#
# This file is part of INSPIRE-SCHEMAS.
# Copyright (C) 2016, 2017 CERN.
#
# INSPIRE-SCHEMAS is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# INSPIRE-SCHEMAS is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with INSPIRE-SCHEMAS; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Public api for methods and functions to handle/verify the jsonschemas."""

from __future__ import absolute_import, division, print_function

import re

from jsonschema import validate as jsonschema_validate

from .errors import SchemaKeyNotFound
from .utils import LocalRefResolver, load_schema


def validate(data, schema_name=None):
    """Validate the given dictionary against the given schema.

    :param data: Dict to validate.
    :type data: dict
    :param schema_name: String with the name of the schema to validate, for
        example, 'authors' or 'jobs'. If `None` passed it will expect for the
        data to have the schema specified in the `$ref` key.
    :type schema_name: str
    :return: None
    :raises inspire_schemas.errors.SchemaNotFound: if the given schema was not
        found.
    :raises inspire_schemas.errors.SchemaKeyNotFound: if the given schema was
        not found.
    :raises jsonschema.SchemaError: if the schema is invalid
    :raises jsonschema.ValidationError: if the data is invalid
    """
    if schema_name is None:
        if '$schema' not in data:
            raise SchemaKeyNotFound(data=data)
        schema_name = data['$schema']

    schema = load_schema(schema_name=schema_name)
    return jsonschema_validate(
        instance=data,
        schema=schema,
        resolver=LocalRefResolver.from_schema(schema),
    )


class LiteratureBuilder(object):
    """Literature Suggestion Builder."""

    def __init__(self, source):
        """Init method.

        :param source: It is the default source, it defines
         the collecting source for the current document.
        :type source: string
        """
        self.obj = {}
        self.source = source

    def _ensure_field(self, field_name, value, obj=None):
        if obj is None:
            obj = self.obj

        if field_name not in obj:
            obj[field_name] = value

    def _get_source(self, source):
        if source is not None:
            return source
        return self.source

    def validate_object(self):
        """Validate the record in according to the hep schema."""
        validate(self.obj, 'hep')

    def add_abstract(self, abstract, source=None):
        """Add abstract.

        :param abstract: abstract for the current document.
        :type abstract: string

        :param source: source for the given abstract.
        :type source: string
        """
        self._ensure_field('abstracts', [])

        self.obj['abstracts'].append({
            'value': abstract.strip(),
            'source': self._get_source(source),
        })

    def add_arxiv_eprint(self, arxiv_id, arxiv_categories):
        """Add arxiv eprint.

        :param arxiv_id: arxiv id for the current document.
        :type arxiv_id: string

        :param arxiv_categories: arXiv categories for the current document.
        :type arxiv_categories: list
        """
        self._ensure_field('arxiv_eprints', [])

        self.obj['arxiv_eprints'].append({
            'value': arxiv_id,
            'categories': arxiv_categories,
        })
        self.obj['citeable'] = True

    def add_doi(self, doi, source=None):
        """Add doi.

        :param doi: doi for the current document.
        :type doi: string

        :param source: source for the current doi.
        :type source: string
        """
        def _doi_normalization(doi_id):
            pattern = (re.compile(r"""
                ((\(?[Dd][Oo][Ii](\s)*\)?:?(\s)*) # 'doi:' or 'doi' or '(doi)'
                |(https?://(dx\.)?doi\.org\/))?   # or 'http://(dx.)doi.org/'
                (?P<doi>10\.                      # 10. (mandatory for DOI's)
                \d{4}                             # [0-9] x4
                (/|%2f)                           # / (possibly urlencoded)
                [\w\-_:;\(\)/\.<>]+               # any character
                [\w\-_:;\(\)/<>])                 # any char except full stop
                """, re.VERBOSE + re.IGNORECASE))
            return pattern.match(doi_id)

        self._ensure_field('dois', [])

        if _doi_normalization(doi):
            self.obj['dois'].append({
                'value': doi,
                'source': self._get_source(source),
            })
            self.obj['citeable'] = True

    def add_author(self, author):
        """Add author.

        :param author: author for a given document.
        :type author: object that comes
        """
        self._ensure_field('authors', [])

        self.obj['authors'].append(author)

    def make_author(self, full_name, affiliations=None, supervisor=False):
        """Make a dictionary that is representing.

        :param full_name: author full name.
        Format: surname, name
        :type author: string

        :param affiliations: author affiliations.
        :type author: [affiliation_0, ..., affiliation_N]

        :param supervisor: it tells if the author is
        a supervisor or not.
        :type supervisor: bool

        :return: dict {fullname:}
        """
        def _verify_author_name_initials(author_name):
            return not bool(re.compile(r'[^A-Z. ]').search(author_name))

        def _normalize_author_name_with_comma(author_name):
            name = author_name.split(',')
            if len(name) > 1 and _verify_author_name_initials(name[1]):
                name[1] = name[1].replace(' ', '')
            name = ', '.join(name)
            return name

        author = {}

        author['full_name'] = _normalize_author_name_with_comma(full_name)

        if affiliations is not None:
            self._ensure_field('affiliations', [], author)
            author['affiliations'].append({
                'value': affiliation
            } for affiliation in affiliations)

        if supervisor is not None:
            author['inspire_roles'] = ['supervisor']

        return author

    def add_inspire_categories(self, subject_terms, source=None):
        """Add inspire categories.

        :param subject_terms: user categories for the current document.
        :type subject_terms: list

        :param source: source for the given categories.
        :type source: string
        """
        self._ensure_field('inspire_categories', [])

        self.obj['inspire_categories'].extend([{
            'term': category,
            'source': self._get_source(source),
        } for category in subject_terms])

    def add_private_notes(self, private_notes, source=None):
        """Add private notes.

        :param private_notes: Hidden notes for the current document.
        :type private_notes: string

        :param source: source for the given private notes.
        :type source: string
        """
        self._ensure_field('_private_notes', [])

        self.obj['_private_notes'].append({
            'value': private_notes,
            'source': self._get_source(source),
        })

    def add_publication_info(self,
                             year=None,
                             cnum=None,
                             artid=None,
                             page_end=None,
                             page_start=None,
                             journal_issue=None,
                             journal_title=None,
                             journal_volume=None):
        """Add publication info.

        :param year: year of publication.
        :type year: integer

        :param cnum: inspire conference number.
        :type cnum: string

        :param artid: article id.
        :type artid: string

        :param page_end: final page for the article.
        :type page_end: string

        :param page_start: initial page for the article.
        :type page_start: string

        :param journal_issue: issue of the journal where
        the document has been published.
        :type journal_issue: string

        :param journal_title: title of the journal where
        the document has been published.
        :type journal_title: string

        :param journal_volume: volume of the journal where
        the document has been published.
        :type journal_volume: string
        """
        self._ensure_field('publication_info', [])

        publication_item = {}
        for key in ('cnum', 'artid', 'page_end', 'page_start',
                    'journal_issue', 'journal_title',
                    'journal_volume', 'year'):
            if locals()[key] is not None:
                publication_item[key] = locals()[key]

        if page_start and page_end:
            try:
                publication_item['number_of_pages'] = int(page_end) - \
                                                      int(page_start) + 1
            except (TypeError, ValueError):
                pass

        self.obj['publication_info'].append(publication_item)

        # Consideration about citeable and refereed attributes
        has_pub_info = all([
            key in self.obj['publication_info'] for key in (
                'year', 'journal_issue', 'journal_volume')])

        has_page_or_artid = any([
            key in self.obj['publication_info'] for key in (
                'page_start', 'page_end', 'artid')])

        if has_pub_info and has_page_or_artid:
            self.obj['citeable'] = True

    def add_imprint_date(self, imprint_date):
        """Add imprint date.

        :param imprint_date: imprint date.
        :type imprint_date: string. A date format is required (yyyy-mm-dd).
        """
        self._ensure_field('imprints', [])

        self.obj['imprints'].append({
            'date': imprint_date
        })

    def add_preprint_date(self, preprint_date):
        """Add imprint date.

        :param preprint_date: preprint date.
        :type preprint_date: string. A date format is required (yyyy-mm-dd).
        """
        self._ensure_field('preprint_date', {})

        self.obj['preprint_date'].append({
            'date': preprint_date
        })

    def add_thesis(self,
                   defense_date=None,
                   degree_type=None,
                   institution=None,
                   date=None):
        """Add thesis info.

        :param defense_date: defense date for the current thesis.
        :type defense_date: string. A date format is required (yyyy-mm-dd).

        :param degree_type: degree type for the current thesis.
        :type degree_type: string

        :param institution: author's affiliation for the current thesis.
        :type institution: string

        :param date: publish date for the current thesis.
        :type date: string. A date format is required (yyyy-mm-dd).
        """
        self._ensure_field('thesis_info', {})

        thesis_item = {}
        for key in ('defense_date', 'degree_type', 'date'):
            if locals()[key] is not None:
                thesis_item[key] = locals()[key].lower()

        if institution is not None:
            thesis_item['institutions'] = [{'name': institution}]

        self.obj['thesis_info'] = thesis_item

    def add_accelerator_experiment(self, experiment):
        """Add accelerator experiment.

        :param experiment: experiment correlated to the current document.
        :type experiment: string
        """
        self._ensure_field('accelerator_experiments', [])

        self.obj['accelerator_experiments'].append({
            'legacy_name': experiment
        })

    def add_language(self, language):
        """Add language.

        :param language: language for the current document.
        :type language: string (2 characters)
        """
        self._ensure_field('languages', [])

        self.obj['languages'].append(language)

    def add_license_url(self, license_url):
        """Add license url.

        :param license_url: url for the description of the license.
        :type license_url: string
        """
        self._ensure_field('license', [])

        self.obj['license'].append({'url': license_url})

    def add_public_note(self, public_notes, source=None):
        """Add public notes.

        :param public_notes: public note for the current article.
        :type public_notes: string

        :param source: source for the given notes.
        :type source: string
        """
        self._ensure_field('public_notes', [])

        self.obj['public_notes'].append({
            'value': public_notes,
            'source': self._get_source(source),
        })

    def add_title(self, title, source=None):
        """Add title.

        :param title: title for the current document.
        :type title: string

        :param source: source for the given title.
        :type source: string
        """
        self._ensure_field('titles', [])

        self.obj['titles'].append({
            'title': title,
            'source': self._get_source(source),
        })

    def add_title_translation(self, title, language, source=None):
        """Add title translation.

        :param title: title translated.
        :type title: string

        :param language: language for the original title.
        :type language: string (2 characters).

        :param source: source for the given title.
        :type source: string
        """
        self._ensure_field('title_translations', [])

        self.obj['title_translations'].append({
            'title': title,
            'language': language,
            'source': self._get_source(source),
        })

    def add_url(self, url):
        """Add url.

        :param url: url for additional information for the current document.
        :type url: string
        """
        self._ensure_field('urls', [])

        self.obj['urls'].append({
            'value': url
        })

    def add_report_numbers(self, report_numbers, source=None):
        """Add report numbers.

        :param report_numbers: report number for the current document.
        :type report_numbers: list [{'report_number': '123'}].

        :param source: source for the given report numbers.
        :type source: string
        """
        self._ensure_field('report_numbers', [])

        self.obj['report_numbers'].extend([{
            'value': report_number.get('report_number', ''),
            'source': self._get_source(source),
        } for report_number in report_numbers])

    def add_collaboration(self, collaboration):
        """Add collaboration.

        :param collaboration: collaboration for the current document.
        :type collaboration: string
        """
        self._ensure_field('collaborations', [])

        self.obj['collaborations'].append({
            'value': collaboration
        })

    def add_acquisition_source(self,
                               submission_number,
                               email=None,
                               source=None,
                               method=None,
                               orcid=None):
        """Add acquisition source.

        :param submission_number: submission number for the suggested document.
        :type submission_number: integer

        :param email: user's mail.
        :type email: integer

        :param source: user's orcid.
        :type source: string

        :param method: method of acquisition for the suggested document.
        :type method: string
        """
        self._ensure_field('acquisition_source', {})

        acquisition_source = {}

        acquisition_source['submission_number'] = str(submission_number)
        acquisition_source['source'] = self._get_source(source)
        for key in ('email', 'method', 'orcid'):
            if locals()[key] is not None:
                acquisition_source[key] = locals()[key]

        self.obj['acquisition_source'] = acquisition_source

    def add_document_type(self, document_type):
        """Add document type.

        :param document_type: document type.
        :type document_type: string
        """
        self._ensure_field('document_type', [])

        self.obj['document_type'].append(document_type)
