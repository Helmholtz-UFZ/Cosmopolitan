"""Information about the crns devices and their datastreams."""

type_id_dict = {
    44: "station",
    85: "station",
    92: "station",
    93: "station",
    94: "station",
    95: "station",
    97: "station",
    99: "station",
    146: "train",
    147: "train",
    148: "train",
    149: "train",
    107: "station",
    162: "station",
    167: "station",
    168: "station",
    170: "station",
    171: "station",
    205: "station",
    216: "train",
}

thing_datastream_dict = {
    44: {
        3180: "Neutron counts",
    },
    85: {
        3762: "Neutron counts",
    },
    92: {
        3716: "Neutron counts",
    },
    93: {
        3808: "Neutron counts",
    },
    94: {
        3898: "Neutron counts",
    },
    95: {
        3921: "Neutron counts",
    },
    97: {
        3831: "Neutron counts",
    },
    99: {
        3739: "Neutron counts",
    },
    146: {
        4172: "Neutron counts",
        4477: "latitude",
        4478: "longitude",
    },
    147: {
        4481: "latitude",
        4482: "longitude",
        4494: "Neutron counts",
    },
    148: {
        4508: "latitude",
        4509: "longitude",
        4521: "Neutron counts",
    },
    149: {
        4535: "latitude",
        4536: "longitude",
        4549: "Neutron counts",
    },
    107: {
        3785: "Neutron counts",
    },
    162: {
        4667: "Neutron counts",
    },
    167: {
        4736: "Neutron counts",
    },
    168: {
        4781: "Neutron counts",
    },
    170: {
        4804: "Neutron counts",
    },
    171: {
        4837: "Neutron counts",
    },
    205: {
        4862: "Neutron counts",
    },
    216: {
        4897: "latitude",
        4898: "longitude",
        4918: "Neutron counts",
    },
}

thing_info_dict = {
    44: "CRNS - Hohes Holz 4m",
    85: "CRNS - Hordorf",
    92: "CRNS - Cunnersdorf",
    93: "CRNS - Grosses Bruch",
    94: "CRNS - Harzgerode",
    95: "CRNS - Falkenberg",
    97: "CRNS - Zugspitze",
    99: "CRNS - Zerbst",
    107: "CRNS - Svalbard",
    146: "CRNS - RR1",
    147: "CRNS - RR2",
    148: "CRNS - RR3",
    149: "CRNS - RR4",
    162: "CRNS Colditz",
    167: "CRNS Klingenthal",
    168: "CRNS Roitzsch",
    170: "CRNS Hoyerswerda",
    171: "CRNS Nossen",
    205: "CRNS Greudnitz",
    216: "CRNS - RR5",
}
ignore_things = [145]
# ignore_things = [
#     145,
#     44,
#     85,
#     92,
#     93,
#     94,
#     95,
#     97,
#     99,
#     107,
#     146,
#     148,
#     149,
#     162,
#     167,
#     168,
#     170,
#     171,
#     205,
#     216,
# ]
