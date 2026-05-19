export const PROVINCES = [
    { id: 2, text: "BALOCHISTAN" },
    { id: 4, text: "AZAD JAMMU AND KASHMIR" },
    { id: 5, text: "CAPITAL TERRITORY" },
    { id: 6, text: "KHYBER PAKHTUNKHWA" },
    { id: 7, text: "PUNJAB" },
    { id: 8, text: "SINDH" },
    { id: 9, text: "GILGIT BALTISTAN" }
];

export function getProvinceTextById(id) {
    const province = PROVINCES.find(
        p => Number(p.id) === Number(id)
    );
    return province ? province.text : "";
}

