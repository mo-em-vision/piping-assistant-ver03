id: material_families
type: taxonomy

metadata:

  title: "Engineering Material Family Classification"

  description:
    >
    Common material classification system used to map materials
    from different standards into common lookup categories.

  purpose:
    - material property lookup
    - pressure design tables
    - allowable stress lookup
    - corrosion tables
    - engineering calculations



families:


  ferritic_steels:

    display_name:
      "Ferritic steels"


    description:
      >
      Iron-based alloys with ferritic microstructure.
      Includes carbon steels, low alloy steels,
      and ferritic stainless steels.


    crystal_structure:
      primary: "BCC"


    includes:


      carbon_steels:

        description:
          "Plain carbon steels used in piping and pressure equipment"


        examples:

          - "ASTM A106"
          - "ASTM A53"
          - "ASTM A516"
          - "ASTM A36"



      low_alloy_steels:

        description:
          >
          Steels containing alloying elements such as chromium,
          molybdenum, nickel in relatively low concentrations.


        examples:

          - "ASTM A335 P11"
          - "ASTM A335 P22"
          - "ASTM A387"



      ferritic_stainless:

        description:
          >
          Stainless steels with ferritic structure.


        examples:

          - "Type 405"
          - "Type 409"
          - "Type 430"



    lookup_tags:

      asme_Y_coefficient:
        value: "ferritic_steels"

      material_group:
        value: "ferrous"



  austenitic_steels:


    display_name:
      "Austenitic steels"


    description:
      >
      Stainless steels and alloys with austenitic microstructure.


    crystal_structure:

      primary: "FCC"


    includes:


      stainless_300_series:

        examples:

          - "ASTM A312 TP304"
          - "ASTM A312 TP316"
          - "Type 304"
          - "Type 316"


      high_alloy_austenitic:

        examples:

          - "904L"
          - "Alloy 800"



    lookup_tags:

      asme_Y_coefficient:
        value: "austenitic_steels"

      material_group:
        value: "ferrous"



  nickel_alloys:


    display_name:
      "Nickel alloys"


    description:
      >
      Nickel-based alloys used for high temperature,
      corrosion resistant applications.


    includes:


      nickel_chromium:

        examples:

          - "Inconel 600"
          - "UNS N06600"


      nickel_iron_chromium:

        examples:

          - "UNS N08800"
          - "UNS N08825"


      precipitation_hardened:

        examples:

          - "UNS N06617"



    lookup_tags:

      asme_Y_coefficient:

        value: "nickel_alloys"

      material_group:

        value: "non_ferrous"



  aluminum_alloys:


    display_name:
      "Aluminum alloys"


    description:
      "Aluminum based engineering alloys"


    examples:

      - "6061-T6"
      - "5083"


    lookup_tags:

      material_group:
        value: "non_ferrous"



  copper_alloys:


    display_name:
      "Copper alloys"


    description:
      "Copper and copper-based alloys"


    examples:

      - "Copper"
      - "Brass"
      - "Bronze"


    lookup_tags:

      material_group:
        value: "non_ferrous"



  titanium_alloys:


    display_name:
      "Titanium alloys"


    description:
      "Titanium based structural alloys"


    examples:

      - "Grade 2 titanium"
      - "Ti-6Al-4V"


    lookup_tags:

      material_group:
        value: "non_ferrous"



  cast_irons:


    display_name:
      "Cast irons"


    description:
      >
      Iron-carbon alloys with high carbon content,
      including gray iron and ductile iron.


    includes:

      gray_iron:

        examples:

          - "ASTM A48"


      ductile_iron:

        examples:

          - "ASTM A536"



    lookup_tags:

      asme_Y_coefficient:

        value: "gray_iron"

      material_group:

        value: "ferrous"



  refractory_materials:


    display_name:
      "Refractory metals"


    examples:

      - "Molybdenum"
      - "Tungsten"
      - "Niobium"


    lookup_tags:

      material_group:
        value: "special"



classification_rules:


  default_mapping:


    if_contains:


      "A106":
        family:
          ferritic_steels


      "A335":
        family:
          ferritic_steels


      "A312 TP304":
        family:
          austenitic_steels


      "A312 TP316":
        family:
          austenitic_steels


      "UNS N06617":
        family:
          nickel_alloys



  confidence:


    exact_match:
      value: 1.0


    standard_match:
      value: 0.9


    inferred_match:
      value: 0.7



validation:


  allowed_families:

    - ferritic_steels
    - austenitic_steels
    - nickel_alloys
    - aluminum_alloys
    - copper_alloys
    - titanium_alloys
    - cast_irons
    - refractory_materials