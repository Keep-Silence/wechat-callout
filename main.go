package main

import (
	"fmt"
	"github.com/go-vgo/robotgo"
	"github.com/vcaesar/imgo"
	"image"
	"image/color"
	_ "image/png"
	"math"
	"os"
)

// 加载图像文件
func loadImage(filename string) (image.Image, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	img, _, err := image.Decode(file)
	if err != nil {
		return nil, err
	}
	return img, nil
}

// 比较两个颜色值，返回是否相似，允许容差
func compareColors(c1, c2 color.Color, tolerance float64) bool {
	r1, g1, b1, a1 := c1.RGBA()
	r2, g2, b2, a2 := c2.RGBA()

	// 如果任何一个像素是透明的，则跳过该像素的比较
	if a1 == 0 || a2 == 0 {
		return true
	}

	// 将颜色值标准化为[0, 1]区间
	r1 /= 257
	g1 /= 257
	b1 /= 257
	r2 /= 257
	g2 /= 257
	b2 /= 257

	// 计算颜色差异（欧几里得距离）
	diff := math.Sqrt(math.Pow(float64(r1)-float64(r2), 2) + math.Pow(float64(g1)-float64(g2), 2) + math.Pow(float64(b1)-float64(b2), 2))

	return diff <= tolerance
}

// 查找子图像，返回位置和匹配度，从右下角开始查找
func findImage(mainImg, searchImg image.Image, tolerance float64) (int, int, bool) {
	mainBounds := mainImg.Bounds()
	searchBounds := searchImg.Bounds()

	// 从主图像的右下角开始遍历
	for y := mainBounds.Dy() - searchBounds.Dy(); y >= 0; y-- {
		for x := mainBounds.Dx() - searchBounds.Dx(); x >= 0; x-- {
			match := true
			// 检查子图像和主图像的匹配情况
			for sy := 0; sy < searchBounds.Dy(); sy++ {
				for sx := 0; sx < searchBounds.Dx(); sx++ {
					mainColor := mainImg.At(x+sx, y+sy)
					searchColor := searchImg.At(sx, sy)

					if !compareColors(mainColor, searchColor, tolerance) {
						match = false
						break
					}
				}
				if !match {
					break
				}
			}
			if match {
				return x, y, true
			}
		}
	}
	return -1, -1, false
}

// 截取全屏并保存为文件
func captureFullScreen(filename string) error {
	// 截取全屏
	bit := robotgo.CaptureScreen()
	if bit == nil {
		os.Exit(1)
	}

	img := robotgo.ToImage(bit)
	imgo.Save(filename, img)

	return nil
}

func main() {
	f, _ := os.CreateTemp("", "*.png")
	defer os.Remove(f.Name())
	// 截取全屏并保存
	err := captureFullScreen(f.Name())
	if err != nil {
		os.Exit(1)
	}

	// 加载主图像和搜索图像
	mainImg, err := loadImage(f.Name())
	if err != nil {
		os.Exit(1)
	}

	searchImg, err := loadImage("wechat.png")
	if err != nil {
		os.Exit(1)
	}

	// 设置容差值
	for i := 90; i >= 80; i = i - 5 {
		// 调用图像查找函数
		x, y, found := findImage(mainImg, searchImg, float64(i))
		if found {
			// 计算子图像中心坐标
			searchBounds := searchImg.Bounds()
			centerX := x + searchBounds.Dx()/2
			centerY := y + searchBounds.Dy()/2

			fmt.Println(centerX, centerY)
			break
		}
	}

}
