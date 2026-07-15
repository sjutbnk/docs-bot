# Index mappings for filling grid and date cells in the МВД notification template tables.

# Table index mappings
PHONE_TABLE = 21
SURNAME_TABLE = 22
NAME_TABLE = 23
PATRONYMIC_TABLE = 24
CITIZENSHIP_TABLE = 25
DOB_TABLE = 26
PASSPORT_TABLE = 28
PASSPORT_ISSUED_T1 = 29
PASSPORT_ISSUED_T2 = 30
PASSPORT_ISSUED_T3 = 31
PATENT_TABLE = 33
PATENT_VALIDITY_TABLE = 36
PROFESSION_TABLE = 41
CONTRACT_DATE_TABLE = 46

# Cell index configurations: (day_indices, month_indices, year_indices, spacer_indices)
DOB_CELLS = ([1, 2], [4, 5], [7, 8, 9, 10], [3, 6])
PASSPORT_DATE_CELLS = ([20, 21], [24, 25], [28, 29, 30, 31], [22, 23, 26, 27])
PATENT_DATE_CELLS = ([21, 22], [25, 26], [29, 30, 31, 32], [23, 24, 27, 28, 33])
PATENT_VALIDITY_START_CELLS = ([1, 2], [4, 5], [7, 8, 9, 10], [3, 6])
PATENT_VALIDITY_END_CELLS = ([12, 13], [15, 16], [18, 19, 20, 21], [14, 17])
CONTRACT_DATE_CELLS = ([1, 2], [4, 5], [8, 9, 10, 11], [3, 6, 7])

# Specific cell mappings for Conclusion / Termination notifications
CONCL_PASSPORT_DATE_CELLS = ([20, 21], [23, 24], [26, 27, 28, 29], [22, 25])
# T33 R1: [20]=D1 [21]=D2 [22]=. [23]=M1 [24]=M2 [25]=. [26]=Y1 [27]=Y2 [28]=Y3 [29]=Y4
CONCL_PATENT_DATE_CELLS = ([20, 21], [23, 24], [26, 27, 28, 29], [22, 25])
# T36 R0 start: [1]=D1 [2]=D2 [3]=. [4]=M1 [5]=M2 [6]=. [7]=Y1..Y4
# T36 R0 end:   [12]=D1 [13]=D2 [14]=. [15]=M1 [16]=M2 [17]=. [18]=Y1..Y4
CONCL_PATENT_VALIDITY_START_CELLS = ([1, 2], [4, 5], [7, 8, 9, 10], [3, 6])
CONCL_PATENT_VALIDITY_END_CELLS = ([12, 13], [15, 16], [18, 19, 20, 21], [14, 17])
CONCL_CONTRACT_DATE_CELLS = ([1, 2], [4, 5], [7, 8, 9, 10], [3, 6])
