/**
 * Fruvia AI — Fruit Knowledge Base / Details Helper
 */
const FruitData = {
  apple: {
    name: "Táo (Apple)",
    scientificName: "Malus domestica",
    family: "Rosaceae (Họ Hoa hồng)",
    calories: "52 kcal / 100g",
    vitamins: "Vitamin C, Vitamin B6, K, Kali, Chất xơ Pectin",
    benefits: "Tốt cho tim mạch, hỗ trợ giảm cân, cải thiện hệ tiêu hóa và kiểm soát đường huyết.",
    origin: "Trung Á"
  },
  avocado: {
    name: "Bơ (Avocado)",
    scientificName: "Persea americana",
    family: "Lauraceae (Họ Lauraceae)",
    calories: "160 kcal / 100g",
    vitamins: "Vitamin E, K, C, B5, B6, Kali, Chất béo đơn không bão hòa",
    benefits: "Giúp sáng mắt, giảm cholesterol xấu, bảo vệ tim mạch và làm đẹp da.",
    origin: "Mexico & Trung Mỹ"
  },
  banana: {
    name: "Chuối (Banana)",
    scientificName: "Musa acuminata",
    family: "Musaceae (Họ Chuối)",
    calories: "89 kcal / 100g",
    vitamins: "Vitamin B6, C, Kali, Magie, Chất xơ",
    benefits: "Cung cấp năng lượng tức thì, giảm căng thẳng cơ bắp, hỗ trợ tiêu hóa và giảm huyết áp.",
    origin: "Đông Nam Á & Úc"
  },
  cherry: {
    name: "Anh Đào (Cherry)",
    scientificName: "Prunus avium",
    family: "Rosaceae (Họ Hoa hồng)",
    calories: "50 kcal / 100g",
    vitamins: "Vitamin C, A, K, Anthocyanin, Melatonin",
    benefits: "Chống viêm mạnh mẽ, cải thiện chất lượng giấc ngủ, giảm đau khớp và bảo vệ tế bào.",
    origin: "Châu Âu & Tây Á"
  },
  grape: {
    name: "Nho (Grape)",
    scientificName: "Vitis vinifera",
    family: "Vitaceae (Họ Nho)",
    calories: "69 kcal / 100g",
    vitamins: "Resveratrol, Vitamin C, K, Đồng, Kali",
    benefits: "Tăng cường sức khỏe tim mạch, chống lão hóa da, cải thiện trí nhớ và ngăn ngừa ung thư.",
    origin: "Địa Trung Hải & Trung Đông"
  },
  guava: {
    name: "Ổi (Guava)",
    scientificName: "Psidium guajava",
    family: "Myrtaceae (Họ Sim)",
    calories: "68 kcal / 100g",
    vitamins: "Vitamin C (gấp 4 lần cam), A, Chất xơ, Folate",
    benefits: "Tăng cường miễn dịch, làm đẹp da, hỗ trợ điều hòa huyết áp và cải thiện chỉ số đường huyết.",
    origin: "Mỹ La-tinh"
  },
  kiwi: {
    name: "Kiwi",
    scientificName: "Actinidia deliciosa",
    family: "Actinidiaceae (Họ Dương đào)",
    calories: "61 kcal / 100g",
    vitamins: "Vitamin C, E, K, Actinidin, Folate, Potassium",
    benefits: "Hỗ trợ tiêu hóa đạm tốt, tăng cường hô hấp, cải thiện giấc ngủ và hệ miễn dịch.",
    origin: "Trung Quốc"
  },
  lemon: {
    name: "Chanh (Lemon)",
    scientificName: "Citrus limon",
    family: "Rutaceae (Họ Cam chanh)",
    calories: "29 kcal / 100g",
    vitamins: "Vitamin C, Citric Acid, Flavonoid, Kali",
    benefits: "Giải độc gan, hỗ trợ tiêu hóa, ngăn ngừa sỏi thận và tăng cường sức đề kháng.",
    origin: "Nam Á"
  },
  lychee: {
    name: "Vải (Lychee)",
    scientificName: "Litchi chinensis",
    family: "Sapindaceae (Họ Bồ hòn)",
    calories: "66 kcal / 100g",
    vitamins: "Vitamin C, Oligonol, Đồng, Polyphenol",
    benefits: "Chống oxy hóa cao, cải thiện lưu thông máu, làm mờ thâm nám và tăng tốc miễn dịch.",
    origin: "Miền Nam Trung Quốc & Việt Nam"
  },
  mango: {
    name: "Xoài (Mango)",
    scientificName: "Mangifera indica",
    family: "Anacardiaceae (Họ Đào lộn hột)",
    calories: "60 kcal / 100g",
    vitamins: "Vitamin A, C, E, Mangiferin, Chất xơ",
    benefits: "Tốt cho mắt, phòng ngừa thoái hóa điểm vàng, cải thiện tiêu hóa và làn da.",
    origin: "Ấn Độ & Đông Nam Á"
  },
  orange: {
    name: "Cam (Orange)",
    scientificName: "Citrus sinensis",
    family: "Rutaceae (Họ Cam chanh)",
    calories: "47 kcal / 100g",
    vitamins: "Vitamin C, Thiamine, Folate, Hesperidin",
    benefits: "Tăng đề kháng mạnh mẽ, giảm nguy cơ sỏi thận, làm dịu huyết áp và mượt da.",
    origin: "Đông Nam Á"
  },
  papaya: {
    name: "Đu Đủ (Papaya)",
    scientificName: "Carica papaya",
    family: "Caricaceae (Họ Đu đủ)",
    calories: "43 kcal / 100g",
    vitamins: "Enzyme Papain, Vitamin C, A, B9, Lycopene",
    benefits: "Hỗ trợ tiêu hóa cực mạnh, chống viêm nhuận tràng, làm lành vết thương và dưỡng da.",
    origin: "Trung Mỹ"
  },
  pear: {
    name: "Lê (Pear)",
    scientificName: "Pyrus communis",
    family: "Rosaceae (Họ Hoa hồng)",
    calories: "57 kcal / 100g",
    vitamins: "Vitamin C, K, Đồng, Chất xơ hòa tan",
    benefits: "Thanh nhiệt nhuận phổi, giảm viêm tiêu sưng, hỗ trợ tiêu hóa nhẹ nhàng.",
    origin: "Châu Âu & Đông Á"
  },
  pineapple: {
    name: "Dứa / Thơm (Pineapple)",
    scientificName: "Ananas comosus",
    family: "Bromeliaceae (Họ Dứa)",
    calories: "50 kcal / 100g",
    vitamins: "Enzyme Bromelain, Vitamin C, Mangan",
    benefits: "Hỗ trợ giảm đau khớp, tiêu hóa đạm tốt, giảm phục hồi tổn thương cơ bắp.",
    origin: "Nam Mỹ"
  },
  pomegranate: {
    name: "Lựu (Pomegranate)",
    scientificName: "Punica granatum",
    family: "Lythraceae (Họ Bàng)",
    calories: "83 kcal / 100g",
    vitamins: "Punicalagin, Axit Punicic, Vitamin C, K",
    benefits: "Chống oxy hóa đỉnh cao, hạ huyết áp, bảo vệ cơ tim và cải thiện trí nhớ.",
    origin: "Iran & Địa Trung Hải"
  },
  strawberry: {
    name: "Dâu Tây (Strawberry)",
    scientificName: "Fragaria × ananassa",
    family: "Rosaceae (Họ Hoa hồng)",
    calories: "32 kcal / 100g",
    vitamins: "Vitamin C, Manganese, Ellagic Acid, Folate",
    benefits: "Kiểm soát lượng đường trong máu, bảo vệ tim, phòng chống ung thư và làm đẹp da.",
    origin: "Châu Âu"
  },
  tomato: {
    name: "Cà Chua (Tomato)",
    scientificName: "Solanum lycopersicum",
    family: "Solanaceae (Họ Cà)",
    calories: "18 kcal / 100g",
    vitamins: "Lycopene, Vitamin C, K, Potassium, Folate",
    benefits: "Bảo vệ tim mạch, phòng ung thư tuyến tiền liệt, chống nắng tự nhiên cho da.",
    origin: "Nam Mỹ"
  },
  watermelon: {
    name: "Dưa Hấu (Watermelon)",
    scientificName: "Citrullus lanatus",
    family: "Cucurbitaceae (Họ Bầu bí)",
    calories: "30 kcal / 100g",
    vitamins: "Lycopene, Citrulline, Vitamin A, C, Nước (92%)",
    benefits: "Bù nước giải nhiệt cấp tốc, giảm đau mỏi cơ bắp, hỗ trợ lưu thông máu và thận.",
    origin: "Châu Phi"
  }
};

/**
 * Helper to get fruit knowledge data by class key
 */
function getFruitDetails(canonicalClass) {
  if (!canonicalClass) return null;
  const key = canonicalClass.toLowerCase().trim();
  return FruitData[key] || {
    name: canonicalClass.charAt(0).toUpperCase() + canonicalClass.slice(1),
    scientificName: "N/A",
    family: "N/A",
    calories: "N/A",
    vitamins: "Vitamin & Khoáng chất tự nhiên",
    benefits: "Cung cấp dinh dưỡng, vitamin và chất xơ tự nhiên cho cơ thể.",
    origin: "N/A"
  };
}
