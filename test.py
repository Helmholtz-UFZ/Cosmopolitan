def parse_crn(file_path):
    def _check_row_length(row, row_index):
        row_length = 6
        if len(row) != row_length:
            raise ValidationError(
                f"Row number {row_index} '{','.join(row)}' has not correct number of columns {row_length}."
            )

    def _check_coordinate(cell, row, row_index):
        # TODO
        min_coordinate = 0
        max_coordinate = 10000000000
        try:
            coor = float(cell)
        except ValueError:
            raise ValidationError(
                f"Cell ''{cell}'' is not a decimal number. Row number {row_index} '{','.join(row)}'."
            )
        if coor < min_coordinate or coor >= max_coordinate:
            raise ValidationError(
                f"Cell '{cell}' needs to be between {min_coordinate} and {max_coordinate}."
                f"Row number {row_index} '{','.join(row)}'."
            )

    def _check_sm(cell, row, row_index, negativ):
        # TODO
        if not negativ:
            min_soil_moisture = 0
            max_soil_moisture = 1
        else:
            min_soil_moisture = -1
            max_soil_moisture = 0

        try:
            sm = float(cell)
        except ValueError:
            raise ValidationError(
                f"Cell '{cell}' is not a decimal number. Row number {row_index} '{','.join(row)}'."
            )
        if sm < min_soil_moisture or sm >= max_soil_moisture:
            raise ValidationError(
                f"Cell '{cell}' needs to be between {min_soil_moisture} and {max_soil_moisture}. "
                f"Row number {row_index} '{','.join(row)}'."
            )

    def _check_row(row, row_index):
        _check_coordinate(row[0], row, row_index)
        _check_coordinate(row[1], row, row_index)

        if not re.match(r"^[0-9]{8}$", row[2]):
            raise ValidationError(
                f"Cell '{row[2]}' is not a day in the format like:'20220323'. Row number {row_index} '{','.join(row)}'."
            )
        try:
            day = datetime.datetime(int(row[2][0:4]), int(row[2][4:6]), int(row[2][6:8]))
        except ValueError:
            raise ValidationError(
                f"Cell '{row[2]}' is not a day in the format like:'20220323'. Row number {row_index} '{','.join(row)}'."
            )

        _check_sm(row[3], row, row_index, False)
        _check_sm(row[4], row, row_index, True)
        _check_sm(row[5], row, row_index, False)

    header_row = [
        "EPSG_UTM_x",
        "EPSG_UTM_y",
        "Day",
        "soil_moisture",
        "err_low",
        "err_high",
    ]

    with open(file_path, "r") as csv_file:
        csv_reader = csv.reader(csv_file)
        # TODO is the first line a header line?
        headers = next(csv_reader)
        _check_row_length(headers, 1)
        # TODO If header line is expected a test like so.
        if not headers == header_row:
            _check_row(headers, 1)

        for row_index, row in enumerate(csv_reader, start=1):
            _check_row(row, row_index)

parse_crn("/home/andersj/Downloads/UQ_AUG18_script_new_format.csv")
