export const formatColoredNumber = (value) => {
    const str = value.toString();
    const [intPart, decimalPart] = str.split(".");

    // white part = everything except the last digit
    const whiteInt = intPart.slice(0, -2);
    const coloredIntDigit = intPart.slice(-1); // last digit before decimal

    // full decimal colored
    const decimal = decimalPart ? `.${decimalPart}` : "";

    const color = value < 200 ? "#f74c43ff" : "#6eee3bff";

    return (
        <>
            {/* white part of integer */}
            <span style={{ color: "#ffffff" }}>{whiteInt}</span>

            {/* last digit before decimal (colored) */}
            <span style={{ color }}>{coloredIntDigit}</span>

            {/* decimal dot + digits (colored) */}
            <span style={{ color }}>{decimal}</span>
        </>
    );
};