node:
  id: "asme_table_304_1_1"
  type: "lookup_table"

  metadata:
    title: "Values of Coefficient Y for t < D/6"
    source_standard: "ASME B31.3"
    table_reference: "Table 304.1.1"
    description: >
      Coefficient Y values used for pressure design calculations when t < D/6.

  purpose:
    output_parameter:
      name: "Y"
      description: "Coefficient Y"

  assumptions:
    - id: "thickness_condition"
      statement: "t < D/6"
      required: true

  parameters:

    inputs:

      - name: "material"
        type: "string"
        required: true
        normalization:
          enabled: true
          aliases:
            ferritic steels:
              - ferritic
              - carbon steel
            austenitic steels:
              - austenitic
              - stainless steel
            nickel alloys:
              - nickel
              - nickel alloy
            gray iron:
              - cast iron
            other ductile metals:
              - ductile metal


      - name: "temperature_c"
        type: "number"
        unit: "°C"
        required: true


    output:

      - name: "Y"
        type: "number"
        unit: "dimensionless"


  lookup:

    method: "linear_interpolation"

    interpolation:

      enabled: true

      formula: >
        Y = Y1 + (Y2-Y1)*(T-T1)/(T2-T1)

      rules:

        - "Temperature points must be sorted ascending"
        - "Interpolation is allowed only between existing table points"
        - "Extrapolation beyond table limits is not allowed unless explicitly enabled"


      extrapolation:
        allowed: false


      validation:

        max_temperature_gap_C:
          enabled: true
          value: 25

        warning_if_exceeded: true


    key:
      x_parameter: "temperature_c"
      y_parameter: "Y"


  data:

    ferritic_steels:

      display_name: "Ferritic steels"

      points:

        - temperature_c: 482
          Y: 0.4

        - temperature_c: 510
          Y: 0.5

        - temperature_c: 538
          Y: 0.7

        - temperature_c: 566
          Y: 0.7

        - temperature_c: 593
          Y: 0.7

        - temperature_c: 621
          Y: 0.7

        - temperature_c: 649
          Y: 0.7

        - temperature_c: 677
          Y: 0.7



    austenitic_steels:

      display_name: "Austenitic steels"

      points:

        - temperature_c: 482
          Y: 0.4

        - temperature_c: 510
          Y: 0.4

        - temperature_c: 538
          Y: 0.4

        - temperature_c: 566
          Y: 0.4

        - temperature_c: 593
          Y: 0.5

        - temperature_c: 621
          Y: 0.7

        - temperature_c: 649
          Y: 0.7

        - temperature_c: 677
          Y: 0.7



    nickel_alloys:

      display_name: "Nickel alloys"

      materials:

        - "UNS N06617"
        - "UNS N08800"
        - "UNS N08810"
        - "UNS N08825"


      points:

        - temperature_c: 482
          Y: 0.4

        - temperature_c: 510
          Y: 0.4

        - temperature_c: 538
          Y: 0.4

        - temperature_c: 566
          Y: 0.4

        - temperature_c: 593
          Y: 0.4

        - temperature_c: 621
          Y: 0.4

        - temperature_c: 649
          Y: 0.5

        - temperature_c: 677
          Y: 0.7



    gray_iron:

      display_name: "Gray iron"

      points:

        - temperature_c: 482
          Y: 0.0


      unavailable_after:
        temperature_c: 482

      behavior:
        if_no_data: "error"



    other_ductile_metals:

      display_name: "Other ductile metals"

      points:

        - temperature_c: 482
          Y: 0.4

        - temperature_c: 510
          Y: 0.4

        - temperature_c: 538
          Y: 0.4

        - temperature_c: 566
          Y: 0.4

        - temperature_c: 593
          Y: 0.4

        - temperature_c: 621
          Y: 0.4

        - temperature_c: 649
          Y: 0.4

        - temperature_c: 677
          Y: 0.4



resolver:

  inputs:

    material:
      source: "user_or_parent_node"

    temperature_c:
      source: "user_or_parent_node"


  process:

    - action: normalize_material

    - action: select_dataset
      using: material

    - action: interpolate
      using:
        x: temperature_c
        y: Y


  output:

    parameter: Y
    verified: true


  errors:

    missing_material:
      severity: "fatal"

    temperature_out_of_range:
      severity: "fatal"

    invalid_assumption:
      severity: "fatal"