node:
  id: "material_ASTM_A106"
  type: "material"

  metadata:

    name: "ASTM A106 Seamless Carbon Steel Pipe"

    standard:
      organization: "ASTM"
      designation: "A106/A106M"
      title: "Seamless Carbon Steel Pipe for High-Temperature Service"

    description:
      >
      Carbon steel pipe material commonly used for high-temperature
      pressure piping service.

  classification:

    material_family:
      value: "ferritic_steels"
      purpose:
        >
        Common classification key used by design tables such as ASME pressure design coefficient tables.

    material_group:
      value: "carbon_steel"

    alloy_type:
      value: "low_alloy_ferritic"

    phase:
      value: "ferritic"


  grades:

    - designation: "Grade A"

    - designation: "Grade B"

    - designation: "Grade C"



  chemistry:

    unit: "wt_percent"

    grade_B:

      carbon_max:
        value: 0.30

      manganese:
        min: 0.29
        max: 1.06

      phosphorus_max:
        value: 0.035

      sulfur_max:
        value: 0.035

      silicon_min:
        value: 0.10


  mechanical_properties:

    grade_B:

      tensile_strength:

        minimum:
          value: 60000
          unit: "psi"

        value_si:
          value: 415
          unit: "MPa"



      yield_strength:

        minimum:
          value: 35000
          unit: "psi"

        value_si:
          value: 240
          unit: "MPa"


      elongation:

        minimum:
          value: 30
          unit: "%"



  temperature_properties:

    applicable_temperature_range:

      min:
        value: "-29"
        unit: "degC"

      note:
        >
        Maximum allowable temperature depends on design code, allowable stress tables, and service conditions.



  physical_properties:


    density:

      value:
        7850
      unit:
        kg_per_m3


    modulus_elasticity:

      value:
        200000
      unit:
        MPa


    poisson_ratio:

      value:
        0.3



  design_properties:


    pressure_design:

      eligible:
        value: true


      related_tables:


        coefficient_Y:

          lookup:

            table_id:
              "ASME_304_1_1_coefficient_Y"

            key_mapping:

              material_family:
                source: "classification.material_family"

              temperature:
                source: "design_temperature"



        allowable_stress:

          lookup:

            table_id:
              "ASME_II_D_allowable_stress"

            key_mapping:

              material:
                source: "ASTM_A106_grade_B"

              temperature:
                source: "design_temperature"



  aliases:

    - "A106"
    - "ASTM A106"
    - "A106 Grade B"
    - "SA106 Grade B"



  verification:


    required_inputs:

      - grade
      - heat_treatment_condition


    assumptions:

      - id: "seamless_pipe"
        statement:
          "Material is seamless pipe"
        required: true


      - id: "carbon_steel_family"
        statement:
          "Material belongs to ferritic carbon steels"
        required: true



  references:


    - document:
        "ASTM A106/A106M"

    - document:
        "ASME BPVC Section VIII Division 1"
