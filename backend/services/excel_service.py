import pandas as pd


def update_excel(
    file_path: str,
    row_index: int,
    extracted_data: dict
):

    print("================================")
    print("Excel file:", file_path)
    print("Row index:", row_index)
    print("Extracted data:", extracted_data)

    # Read Excel
    df = pd.read_excel(file_path)

    print("Excel columns:")
    print(df.columns.tolist())

    print("Before update:")
    print(df.iloc[row_index].to_dict())

    # Convert columns to object so both text and numbers can be inserted
    for field in extracted_data.keys():

        if field in df.columns:
            df[field] = df[field].astype("object")

    # Update fields
    for field, value in extracted_data.items():

        if field not in df.columns:
            print(f"Column not found: {field}")
            continue

        current_value = df.at[row_index, field]

        print(
            f"Field: {field} | "
            f"Current: {current_value} | "
            f"New: {value}"
        )

        # Only update empty cells
        if pd.isna(current_value) or str(current_value).strip() == "":

            if value is not None:
                df.at[row_index, field] = value
                print(f"Updated {field} -> {value}")

    print("After update:")
    print(df.iloc[row_index].to_dict())

    # Save Excel
    df.to_excel(file_path, index=False)

    print("Excel saved successfully.")
    print("================================")

    return df