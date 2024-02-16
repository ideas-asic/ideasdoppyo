
common_header_format = [('Packet ID', '>u2'),
                ('Packet Sequence', '>u2'),
                ('Timestamp', '>u4'),
                ('Data Length', '>u2')]


# Pipeline ASIC ------------------------------------------------------
pipeline_header_format = [('Source ID', '>u1'),
      ('Trigger Type', '>u1'),
      ('Status', '>u2'),
      ('ASIC Dout', '>u2'),
      ('Event ID', '>u4'),
      ('PPS Timestamp', '>u4')]

pipeline_data_format = [('Cell' + str(i), '>u2') for i in range(160)]

pipeline_sampling_format = pipeline_header_format + pipeline_data_format

# --------------------------------------------------------------------
