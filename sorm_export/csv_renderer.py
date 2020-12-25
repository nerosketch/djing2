import csv
from io import StringIO

from rest_framework.renderers import BaseRenderer

from logging import getLogger
log = getLogger(__name__)


class CSVRenderer(BaseRenderer):
    """
    Renderer which serializes to CSV
    """

    media_type = 'text/csv'
    format = 'csv'
    level_sep = '.'
    labels = None  # {'<field>':'<label>'}
    writer_opts = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Renders serialized *data* into CSV.
        """
        if not data:
            return (),

        writer_opts = self.writer_opts or {}

        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer, dialect='unix', **writer_opts)
        for row_data in data:
            row = (eld for elt, eld in row_data.items())
            csv_writer.writerow(row)
        # csv_writer.writerows(data)

        return csv_buffer.getvalue().encode()
